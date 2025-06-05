"""Service layer for managing chat balances."""

from db import Database


class Account:
    """Gateway for chat balance operations."""

    def __init__(self, db: Database):
        self.db = db

    def get_balance(self, chat_id: int) -> float:
        """Return current balance for the given chat."""
        return self.db.get_balance(chat_id)

    def pop_up(self, chat_id: int, amount: float) -> None:
        """Increase the chat balance by amount."""
        balance = self.get_balance(chat_id) + amount
        self.db.save_balance(chat_id, balance)

    def charge(self, chat_id: int, amount: float) -> None:
        """Deduct amount from the chat balance."""
        balance = self.get_balance(chat_id) - amount
        self.db.save_balance(chat_id, balance)
