"""Gateways externos (fictícios). Em produção seriam chamadas HTTP reais."""
import logging
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


class AntiFraudGateway(Protocol):
    def notify(self, payload: dict) -> bool: ...


class RegistryValidator(Protocol):
    """Validação cadastral (ex.: consulta de CPF)."""

    def is_valid(self, document: str) -> bool: ...


class WebhookAntiFraudGateway:
    def __init__(self, url: str, timeout: float = 2.0):
        self.url = url
        self.timeout = timeout

    def notify(self, payload: dict) -> bool:
        try:
            r = httpx.post(self.url, json=payload, timeout=self.timeout)
            return r.status_code < 300
        except httpx.HTTPError as exc:
            log.warning("Falha ao notificar anti-fraude: %s", exc)
            return False


class NullAntiFraudGateway:
    """Usado quando ANTIFRAUD_URL não está configurada."""

    def notify(self, payload: dict) -> bool:
        return True


class SimpleRegistryValidator:
    """Aceita documentos com 11 dígitos (simulação de consulta cadastral)."""

    def is_valid(self, document: str) -> bool:
        return document.isdigit() and len(document) == 11
