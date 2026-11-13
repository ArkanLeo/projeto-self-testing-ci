import sqlite3
import threading


class Database:
    """SQLite com uma única conexão compartilhada + lock (serializa escritas)."""

    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self._create_schema()

    def _create_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                document TEXT NOT NULL,
                balance INTEGER NOT NULL CHECK (balance >= 0)
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('debit','credit')),
                amount INTEGER NOT NULL,
                counterparty_id INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency (
                key TEXT PRIMARY KEY,
                response TEXT NOT NULL
            );
            """
        )
        self.conn.commit()
