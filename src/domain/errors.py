class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidAmount(DomainError):
    status_code = 422


class InsufficientFunds(DomainError):
    status_code = 409


class AccountNotFound(DomainError):
    status_code = 404


class InvalidAccount(DomainError):
    status_code = 422


class SameAccountTransfer(DomainError):
    status_code = 422


class InvalidFilter(DomainError):
    status_code = 422
