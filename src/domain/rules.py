"""Regras puras de negócio. Valores monetários sempre em centavos (int)."""
from .errors import InsufficientFunds, InvalidAmount, SameAccountTransfer


def validate_amount(amount: int) -> int:
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise InvalidAmount("O valor deve ser um inteiro positivo (centavos)")
    return amount


def apply_transfer(balance_from: int, balance_to: int, amount: int, same_account: bool = False):
    """Retorna (novo_saldo_origem, novo_saldo_destino)."""
    if same_account:
        raise SameAccountTransfer("Origem e destino devem ser diferentes")
    validate_amount(amount)
    if balance_from < amount:
        raise InsufficientFunds("Saldo insuficiente")
    return balance_from - amount, balance_to + amount
