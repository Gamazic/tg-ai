import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta
from aiogram.exceptions import TelegramAPIError
from db import Database, Message
from ai import AskService
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get token and API key from environment variables
TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

if not TOKEN or not API_KEY:
    raise ValueError("BOT_TOKEN and API_KEY must be set in .env file")

# Initialize bot and dispatcher with memory storage
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)
msg_db = Database()
service = AskService(
    API_KEY,
    msg_db,
    max_completion_tokens=1000,
    max_history_depth=1000,
    max_context_words=10000,
)


class DateState(StatesGroup):
    waiting_for_date = State()


@dp.message(Command("ask_days_context"))
async def ask_days_context_command(message: types.Message):
    """Handle the /ask_days_context command with number of days and question text"""
    if message.text is None:
        await message.answer("Please provide valid number of days")
        return
    # Split command and get number of days and question
    command_parts = message.text.split(" ", maxsplit=2)
    if len(command_parts) != 3:
        await message.answer("Please use format: /ask_days_context <days> <question>")
        return

    try:
        days = int(command_parts[1])
    except ValueError:
        await message.answer("Please provide valid number of days")
        return

    if days <= 0:
        await message.answer("Number of days should be positive")
        return

    # Get question text
    question = command_parts[2]

    # Calculate start date
    start_date = datetime.now() - timedelta(days=days)

    # Get answer from AI service
    answer = service.ask(
        question,
        message.chat.id,
        start_date,
        Message(
            message.chat.id,
            message.date,
            message.from_user.id,
            message.from_user.username,
            message.text,
        ),
    )
    await message.answer(answer)


@dp.message(Command("ask_today"))
async def ask_today_command(message: types.Message):
    """Handle the /ask_today command with just a question"""
    if message.text is None:
        await message.answer("Please provide a question")
        return

    # Split command and get question
    command_parts = message.text.split(" ", maxsplit=1)
    if len(command_parts) != 2:
        await message.answer("Please use format: /ask_today <question>")
        return

    # Get question text
    question = command_parts[1]

    # Get answer from AI service using start of today as context start date
    start_date = datetime.now() - timedelta(days=1)
    answer = service.ask(
        question,
        message.chat.id,
        start_date,
        Message(
            message.chat.id,
            message.date,
            message.from_user.id,
            message.from_user.username,
            message.text,
        ),
    )
    await message.answer(answer)


@dp.message(Command("ask_no_context"))
async def ask_no_context_command(message: types.Message):
    """Handle the /ask_no_context command with just a question"""
    if message.text is None:
        await message.answer("Please provide a question")
        return

    # Split command and get question
    command_parts = message.text.split(" ", maxsplit=1)
    if len(command_parts) != 2:
        await message.answer("Please use format: /ask_no_context <question>")
        return

    # Get question text
    question = command_parts[1]

    # Get answer from AI service using current time as start date
    answer = service.ask(
        question,
        message.chat.id,
        datetime.now(),
        Message(
            message.chat.id,
            message.date,
            message.from_user.id,
            message.from_user.username,
            message.text,
        ),
    )
    await message.answer(answer)


@dp.message(Command("ask_datetime_context"))
async def ask_datetime_context_command(message: types.Message):
    """Handle the /ask_datetime_context command with datetime and question text"""
    # Split command and get datetime and question
    if message.text is None:
        await message.answer("Please provide valid date in format DD-MM-YYYY")
        return

    command_parts = message.text.split(" ", maxsplit=2)
    if len(command_parts) != 3:
        await message.answer(
            "Please use format: /ask_datetime_context <DD-MM-YYYY> <question>"
        )
        return

    try:
        start_date = datetime.strptime(command_parts[1], "%d-%m-%Y")
    except ValueError:
        await message.answer("Please provide valid date in format DD-MM-YYYY")
        return

    # Get question text
    question = command_parts[2]

    # Get answer from AI service
    answer = service.ask(
        question,
        message.chat.id,
        start_date,
        Message(
            message.chat.id,
            message.date,
            message.from_user.id,
            message.from_user.username,
            message.text,
        ),
    )
    await message.answer(answer)


@dp.message(Command("spent"))
async def spent_command(message: types.Message):
    """Handle the /spent command to get total spend for the chat"""
    total_spend = msg_db.get_total_spend(message.chat.id)
    await message.answer(f"Total spend for this chat: ${total_spend:.6f}")


@dp.message(Command("ask"))
async def ask_command(message: types.Message):
    """Handle the /ask command with or without reply"""
    if not message.reply_to_message:
        # Handle as no context ask
        command_parts = message.text.split(" ", maxsplit=1)
        if len(command_parts) != 2:
            await message.answer("Please provide a question after /ask")
            return

        question = command_parts[1]
        answer = service.ask(
            question,
            message.chat.id,
            datetime.now(),
            Message(
                message.chat.id,
                message.date,
                message.from_user.id,
                message.from_user.username,
                message.text,
            ),
        )
        await message.answer(answer)
        return

    # Get the original message that was replied to
    original_text = message.reply_to_message.text
    if not original_text:
        await message.answer("Cannot process empty or non-text message")
        return

    # Get answer from AI service using today's context
    answer = service.ask(
        original_text,
        message.chat.id,
        datetime.now(),
        Message(
            message.chat.id,
            message.date,
            message.from_user.id,
            message.from_user.username,
            message.text,
        ),
    )
    await message.answer(answer)


# handle every message in group
@dp.message()
async def handle_message(message: types.Message):
    """Handle every message in group"""
    msg_db.save_msg(
        Message(
            message.chat.id,
            message.date,
            message.from_user.id,
            message.from_user.username,
            message.text or "",  # Use empty string if text is None
        )
    )


if __name__ == "__main__":
    import logging

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting bot...")
        asyncio.run(
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        )
    except Exception as e:
        logger.error(f"Error occurred while running the bot: {e}")
        raise
