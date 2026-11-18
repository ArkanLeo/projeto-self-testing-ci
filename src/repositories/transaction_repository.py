import json
from datetime import UTC, datetime

from .db import Database


class TransactionRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, account_id, type_, amount, counterparty_id, created_at: str | None = None):
        created_at = created_at or datetime.now(UTC).isoformat()
        self.db.conn.execute(
            "INSERT INTO transactions (account_id,type,amount,counterparty_id,created_at) VALUES (?,?,?,?,?)",
            (account_id, type_, amount, counterparty_id, created_at),
        )

    def list(self, account_id, type_=None, date_from=None, date_to=None) -> list:
        sql = "SELECT * FROM transactions WHERE account_id=?"
        params: list = [account_id]
        if type_:
            sql += " AND type=?"
            params.append(type_)
        if date_from:
            sql += " AND substr(created_at,1,10) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND substr(created_at,1,10) <= ?"
            params.append(date_to)
        sql += " ORDER BY id"
        return [dict(r) for r in self.db.conn.execute(sql, params).fetchall()]

    # idempotência
    def get_idempotent(self, key: str):
        row = self.db.conn.execute("SELECT response FROM idempotency WHERE key=?", (key,)).fetchone()
        return json.loads(row["response"]) if row else None

    def save_idempotent(self, key: str, response: dict):
        self.db.conn.execute(
            "INSERT INTO idempotency (key,response) VALUES (?,?)", (key, json.dumps(response))
        )
