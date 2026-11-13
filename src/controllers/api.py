import os

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.domain.errors import DomainError
from src.repositories.account_repository import AccountRepository
from src.repositories.db import Database
from src.repositories.transaction_repository import TransactionRepository
from src.services.gateways import NullAntiFraudGateway, SimpleRegistryValidator, WebhookAntiFraudGateway
from src.services.wallet_service import WalletService


class AccountIn(BaseModel):
    owner: str
    document: str
    initial_balance: int = 0


class TransferIn(BaseModel):
    from_account: int
    to_account: int
    amount: int


def build_service(db=None, antifraud=None, registry=None) -> WalletService:
    db = db or Database(os.getenv("DB_PATH", ":memory:"))
    if antifraud is None:
        url = os.getenv("ANTIFRAUD_URL")
        antifraud = WebhookAntiFraudGateway(url) if url else NullAntiFraudGateway()
    return WalletService(db, AccountRepository(db), TransactionRepository(db),
                         antifraud, registry or SimpleRegistryValidator())


def create_app(service: WalletService | None = None) -> FastAPI:
    app = FastAPI(title="Wallet API")
    svc = service or build_service()

    @app.exception_handler(DomainError)
    async def domain_handler(_: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/accounts", status_code=201)
    def create_account(body: AccountIn):
        return svc.create_account(body.owner, body.document, body.initial_balance)

    @app.get("/accounts/{account_id}")
    def get_account(account_id: int):
        return svc.get_account(account_id)

    @app.post("/transfers")
    def transfer(body: TransferIn, idempotency_key: str | None = Header(default=None)):
        return svc.transfer(body.from_account, body.to_account, body.amount, idempotency_key)

    @app.get("/accounts/{account_id}/statement")
    def statement(account_id: int, type: str | None = None,
                  date_from: str | None = None, date_to: str | None = None):
        return svc.statement(account_id, type, date_from, date_to)

    return app


app = create_app()
