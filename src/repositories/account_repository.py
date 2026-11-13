
from .db import Database


class AccountRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, owner: str, document: str, balance: int) -> dict:
        cur = self.db.conn.execute(
            "INSERT INTO accounts (owner, document, balance) VALUES (?,?,?)",
            (owner, document, balance),
        )
        return self.get(cur.lastrowid)

    def get(self, account_id: int) -> dict | None:
        row = self.db.conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        return dict(row) if row else None

    def set_balance(self, account_id: int, balance: int) -> None:
        self.db.conn.execute("UPDATE accounts SET balance=? WHERE id=?", (balance, account_id))
