from unittest.mock import Mock

import pytest

from src.repositories.account_repository import AccountRepository
from src.repositories.db import Database
from src.repositories.transaction_repository import TransactionRepository
from src.services.wallet_service import WalletService


class RegistryStub:
    """Stub: devolve sempre respostas fixas (CPFs terminados em 0 são 'inválidos')."""

    def is_valid(self, document: str) -> bool:
        return not document.endswith("0")


@pytest.fixture
def antifraud():
    return Mock()


@pytest.fixture
def service(antifraud):
    db = Database(":memory:")
    return WalletService(db, AccountRepository(db), TransactionRepository(db),
                         antifraud, RegistryStub())
