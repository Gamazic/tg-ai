#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found!"
    exit 1
fi

# Configuration
REMOTE_USER="${DEPLOY_USER}"
REMOTE_HOST="${DEPLOY_HOST}"
REMOTE_DIR="${DEPLOY_DIR}"
FILES="ai.py bot.py db.py requirements.txt .env"

# Validate required environment variables
if [ -z "$DEPLOY_USER" ] || [ -z "$DEPLOY_HOST" ] || [ -z "$DEPLOY_DIR" ]; then
    echo "❌ Missing required environment variables in .env file!"
    echo "Please ensure DEPLOY_USER, DEPLOY_HOST, and DEPLOY_DIR are set."
    exit 1
fi

echo "Starting deployment process..."

# Sync files to remote server
echo "Syncing files to remote server..."
rsync -avz --progress $FILES $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR

# Install dependencies
echo "Installing dependencies..."
ssh -o BatchMode=yes $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && source env/bin/activate && pip install -r requirements.txt"

# Kill existing Python process if running
echo "Checking for existing bot process..."
ssh -o BatchMode=yes $REMOTE_USER@$REMOTE_HOST "pkill -f 'python.*bot.py' || true"

# Wait a moment for the process to fully terminate
sleep 2

# Start the bot in the background with proper logging
echo "Starting the bot..."
ssh -f $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && source env/bin/activate && nohup python -u bot.py > bot.log 2>&1 &"

# Wait a moment for the process to start
sleep 5

# Check if the process is running and show recent logs
PROCESS_CHECK=$(ssh -o BatchMode=yes $REMOTE_USER@$REMOTE_HOST "pgrep -f 'python.*bot.py' || true")
if [ -n "$PROCESS_CHECK" ]; then
    echo "✅ Bot process is running."
    ssh -o BatchMode=yes $REMOTE_USER@$REMOTE_HOST "tail -n 10 $REMOTE_DIR/bot.log"
else
    echo "❌ Bot process failed to start!"
    echo "📝 Last logs:"
    ssh -o BatchMode=yes $REMOTE_USER@$REMOTE_HOST "tail -n 50 $REMOTE_DIR/bot.log"
    exit 1
fi