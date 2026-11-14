import logging
from datetime import date

from src.domain.errors import AccountNotFound, InvalidAccount, InvalidFilter
from src.domain.rules import apply_transfer, validate_amount
from src.repositories.account_repository import AccountRepository
from src.repositories.db import Database
from src.repositories.transaction_repository import TransactionRepository

log = logging.getLogger(__name__)


class WalletService:
    def __init__(self, db: Database, accounts: AccountRepository, txs: TransactionRepository,
                 antifraud, registry):
        self.db = db
        self.accounts = accounts
        self.txs = txs
        self.antifraud = antifraud
        self.registry = registry

    def create_account(self, owner: str, document: str, initial_balance: int = 0) -> dict:
        if not owner or not owner.strip():
            raise InvalidAccount("Nome do titular é obrigatório")
        if initial_balance < 0:
            raise InvalidAccount("Saldo inicial não pode ser negativo")
        if not self.registry.is_valid(document):
            raise InvalidAccount("Documento inválido na validação cadastral")
        with self.db.lock:
            acc = self.accounts.create(owner.strip(), document, initial_balance)
            self.db.conn.commit()
        return acc

    def get_account(self, account_id: int) -> dict:
        acc = self.accounts.get(account_id)
        if not acc:
            raise AccountNotFound(f"Conta {account_id} não encontrada")
        return acc

    def transfer(self, from_id: int, to_id: int, amount: int, idempotency_key: str | None = None) -> dict:
        validate_amount(amount)
        with self.db.lock:  # serializa transferências -> sem corrida de saldo
            if idempotency_key:
                previous = self.txs.get_idempotent(idempotency_key)
                if previous:
                    return {**previous, "replayed": True}

            src, dst = self.get_account(from_id), self.get_account(to_id)
            try:
                new_src, new_dst = apply_transfer(src["balance"], dst["balance"], amount, from_id == to_id)
                self.accounts.set_balance(from_id, new_src)
                self.accounts.set_balance(to_id, new_dst)
                self.txs.add(from_id, "debit", amount, to_id)
                self.txs.add(to_id, "credit", amount, from_id)
                result = {"from": from_id, "to": to_id, "amount": amount,
                          "from_balance": new_src, "to_balance": new_dst, "replayed": False}
                if idempotency_key:
                    self.txs.save_idempotent(idempotency_key, result)
                self.db.conn.commit()
            except Exception:
                self.db.conn.rollback()
                raise

        # fora do lock: serviço externo lento não trava as demais transferências
        self.antifraud.notify({"from": from_id, "to": to_id, "amount": amount})
        return result

    def statement(self, account_id: int, tx_type: str | None = None,
                  date_from: str | None = None, date_to: str | None = None) -> list:
        self.get_account(account_id)
        if tx_type not in (None, "debit", "credit"):
            raise InvalidFilter("type deve ser 'debit' ou 'credit'")
        for d in (date_from, date_to):
            if d:
                try:
                    date.fromisoformat(d)
                except ValueError:
                    raise InvalidFilter("Datas devem estar no formato AAAA-MM-DD")
        if date_from and date_to and date_from > date_to:
            raise InvalidFilter("date_from não pode ser posterior a date_to")
        return self.txs.list(account_id, tx_type, date_from, date_to)
