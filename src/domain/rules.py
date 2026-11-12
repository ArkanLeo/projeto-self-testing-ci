from .errors import InsufficientFunds, InvalidAmount, SameAccountTransfer


def validate_amount(amount):
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise InvalidAmount("O valor deve ser um inteiro positivo (centavos)")
    return amount


def apply_transfer(balance_from, balance_to, amount, same_account=False):
    if same_account:
        raise SameAccountTransfer("Origem e destino devem ser diferentes")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise InvalidAmount("O valor deve ser um inteiro positivo (centavos)")
    if balance_from < amount:
        raise InsufficientFunds("Saldo insuficiente")
    return balance_from - amount, balance_to + amount
