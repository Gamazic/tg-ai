from datetime import datetime
from dataclasses import dataclass
import os
from file_read_backwards import FileReadBackwards


@dataclass
class Message:
    chat_id: int
    datetime: datetime
    user_id: int
    username: str
    text: str


class Database:
    def __init__(self):
        # Initialize dictionary to store file descriptors
        self.files = {}
        self.max_history_depth = 10000
        self.spend_files = {}

    def save_msg(self, msg: Message):
        # for every chat id create a new file and save the message if file not exists
        # save descriptor to field of database

        # check if file exists is descriptors dict
        if msg.chat_id not in self.files:
            # Open file for writing
            filename = self.__file_name(msg.chat_id)
            self.files[msg.chat_id] = open(filename, "a", encoding="utf-8")

        # Write message to file
        date_ts = int(msg.datetime.timestamp())
        # put escape symbols to text
        text = msg.text.replace("\n", "\\n")
        message = f"{date_ts},{msg.user_id},{msg.username},{text}\n"
        self.files[msg.chat_id].write(message)
        self.files[msg.chat_id].flush()  # Ensure message is written immediately

    def get_messages(
        self, chat_id: int, start_date: datetime, end_date: datetime, limit: int = 1000
    ) -> list[Message]:
        # check if file exist on disk
        filename = self.__file_name(chat_id)
        if not os.path.exists(filename):
            return []

        # read all messages from file
        messages = []
        history_depth = 0
        with FileReadBackwards(filename, encoding="utf-8") as frb:
            for line in frb:
                date_ts, user_id, username, text = line.split(",", maxsplit=3)
                dt = datetime.fromtimestamp(float(date_ts))
                if start_date <= dt <= end_date:
                    messages.append(Message(chat_id, dt, int(user_id), username, text))
                else:
                    break

                history_depth += 1
                if history_depth > self.max_history_depth or history_depth > limit:
                    break

        return messages[::-1]

    def __file_name(self, chat_id: int) -> str:
        return f"chat_{chat_id}.txt"

    def save_spend(self, chat_id: int, spend: float, dt: datetime):
        filename = self.__spend_file_name(chat_id)
        if chat_id not in self.spend_files:
            self.spend_files[chat_id] = open(filename, "a", encoding="utf-8")

        date_ts = int(dt.timestamp())
        self.spend_files[chat_id].write(f"{date_ts},{spend}\n")
        self.spend_files[chat_id].flush()

    def get_total_spend(self, chat_id: int) -> float:
        filename = self.__spend_file_name(chat_id)
        if not os.path.exists(filename):
            return 0

        total_spend = 0
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                _, spend = line.split(",", maxsplit=1)
                total_spend += float(spend)

        return total_spend

    def __spend_file_name(self, chat_id: int) -> str:
        return f"spend_{chat_id}.txt"
