import threading
from unittest.mock import Mock

import pytest

from src.domain.errors import (
    AccountNotFound,
    InsufficientFunds,
    InvalidAccount,
    InvalidAmount,
    InvalidFilter,
    SameAccountTransfer,
)
from src.services.gateways import NullAntiFraudGateway, SimpleRegistryValidator, WebhookAntiFraudGateway

DOC_A, DOC_B = "12345678901", "10987654321"


def two_accounts(service, a=1000, b=0):
    x = service.create_account("Ana", DOC_A, a)
    y = service.create_account("Beto", DOC_B, b)
    return x["id"], y["id"]


# ---------- contas (Stub de validação cadastral) ----------
def test_cria_e_consulta_conta(service):
    acc = service.create_account("  Ana ", DOC_A, 500)
    assert service.get_account(acc["id"])["balance"] == 500
    assert acc["owner"] == "Ana"


def test_documento_reprovado_pelo_stub_cadastral(service):
    with pytest.raises(InvalidAccount):
        service.create_account("Ana", "12345678900", 0)  # termina em 0 -> stub reprova


def test_nome_vazio_e_saldo_negativo(service):
    with pytest.raises(InvalidAccount):
        service.create_account("  ", DOC_A, 0)
    with pytest.raises(InvalidAccount):
        service.create_account("Ana", DOC_A, -1)


def test_conta_inexistente(service):
    with pytest.raises(AccountNotFound):
        service.get_account(999)


# ---------- transferência (Mock do anti-fraude) ----------
def test_transferencia_atualiza_saldos_e_notifica_antifraude_uma_vez(service, antifraud):
    a, b = two_accounts(service)
    r = service.transfer(a, b, 300)
    assert (r["from_balance"], r["to_balance"]) == (700, 300)
    antifraud.notify.assert_called_once_with({"from": a, "to": b, "amount": 300})


def test_transferencia_falha_nao_notifica_nem_altera_saldos(service, antifraud):
    a, b = two_accounts(service, 100, 0)
    with pytest.raises(InsufficientFunds):
        service.transfer(a, b, 500)
    antifraud.notify.assert_not_called()
    assert service.get_account(a)["balance"] == 100
    assert service.statement(a) == []


def test_transferencia_para_si_mesmo_e_valor_invalido(service):
    a, b = two_accounts(service)
    with pytest.raises(SameAccountTransfer):
        service.transfer(a, a, 10)
    with pytest.raises(InvalidAmount):
        service.transfer(a, b, 0)


def test_transferencia_com_conta_inexistente(service):
    a, _ = two_accounts(service)
    with pytest.raises(AccountNotFound):
        service.transfer(a, 999, 10)


def test_idempotencia_repete_resposta_sem_duplicar(service, antifraud):
    a, b = two_accounts(service)
    r1 = service.transfer(a, b, 100, "chave-1")
    r2 = service.transfer(a, b, 100, "chave-1")
    assert r1["replayed"] is False and r2["replayed"] is True
    assert service.get_account(a)["balance"] == 900
    assert antifraud.notify.call_count == 1


def test_concorrencia_nao_gera_saldo_negativo_nem_perde_dinheiro(service):
    a, b = two_accounts(service, 1000, 0)
    results = []

    def worker():
        try:
            service.transfer(a, b, 100)
            results.append("ok")
        except InsufficientFunds:
            results.append("sem_saldo")

    threads = [threading.Thread(target=worker) for _ in range(30)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("ok") == 10
    assert service.get_account(a)["balance"] == 0
    assert service.get_account(b)["balance"] == 1000


def test_falha_no_antifraude_nao_desfaz_transferencia(service, antifraud):
    antifraud.notify.return_value = False
    a, b = two_accounts(service)
    service.transfer(a, b, 50)
    assert service.get_account(b)["balance"] == 50


# ---------- extrato ----------
def test_extrato_com_filtro_de_tipo(service):
    a, b = two_accounts(service)
    service.transfer(a, b, 100)
    service.transfer(b, a, 30)
    assert [t["type"] for t in service.statement(a)] == ["debit", "credit"]
    assert [t["amount"] for t in service.statement(a, tx_type="debit")] == [100]


def test_extrato_com_filtro_de_data(service):
    a, b = two_accounts(service)
    service.transfer(a, b, 100)
    service.txs.add(a, "credit", 5, b, "2020-01-15T10:00:00+00:00")
    service.txs.add(a, "credit", 7, b, "2020-01-31T23:59:00+00:00")  # último dia do período
    assert len(service.statement(a, date_from="2020-01-01", date_to="2020-01-31")) == 2
    assert len(service.statement(a, date_from="2999-01-01")) == 0
    assert len(service.statement(a, date_to="2020-12-31")) == 2


def test_extrato_filtros_invalidos(service):
    a, _ = two_accounts(service)
    with pytest.raises(InvalidFilter):
        service.statement(a, tx_type="pix")
    with pytest.raises(InvalidFilter):
        service.statement(a, date_from="ontem")
    with pytest.raises(InvalidFilter):
        service.statement(a, date_from="2024-02-01", date_to="2024-01-01")


# ---------- gateways ----------
def test_webhook_gateway_ok_e_falha(monkeypatch):
    import httpx
    gw = WebhookAntiFraudGateway("http://antifraude.local/hook")
    monkeypatch.setattr(httpx, "post", Mock(return_value=Mock(status_code=202)))
    assert gw.notify({"x": 1}) is True
    monkeypatch.setattr(httpx, "post", Mock(side_effect=httpx.ConnectError("fora do ar")))
    assert gw.notify({"x": 1}) is False


def test_gateways_padrao():
    assert NullAntiFraudGateway().notify({}) is True
    assert SimpleRegistryValidator().is_valid("12345678901")
    assert not SimpleRegistryValidator().is_valid("abc")


def test_mesma_chave_de_idempotencia_em_paralelo_cobra_uma_vez(service):
    a, b = two_accounts(service)
    erros, resultados = [], []

    def worker():
        try:
            resultados.append(service.transfer(a, b, 100, "chave-paralela"))
        except Exception as exc:  # noqa: BLE001
            erros.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert erros == []
    assert sum(1 for r in resultados if not r["replayed"]) == 1
    assert service.get_account(a)["balance"] == 900
