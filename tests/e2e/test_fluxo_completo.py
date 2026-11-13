from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from src.controllers.api import build_service, create_app


@pytest.fixture
def client():
    return TestClient(create_app(build_service()))


def conta(client, nome, doc, saldo):
    r = client.post("/accounts", json={"owner": nome, "document": doc, "initial_balance": saldo})
    assert r.status_code == 201
    return r.json()["id"]


def test_fluxo_registro_transferencia_e_extrato(client):
    ana = conta(client, "Ana", "12345678901", 1000)
    beto = conta(client, "Beto", "10987654321", 0)

    r = client.post("/transfers", json={"from_account": ana, "to_account": beto, "amount": 250},
                    headers={"Idempotency-Key": "k1"})
    assert r.status_code == 200 and r.json()["from_balance"] == 750

    # repetir a mesma chave não cobra de novo
    r = client.post("/transfers", json={"from_account": ana, "to_account": beto, "amount": 250},
                    headers={"Idempotency-Key": "k1"})
    assert r.json()["replayed"] is True
    assert client.get(f"/accounts/{ana}").json()["balance"] == 750

    extrato = client.get(f"/accounts/{beto}/statement", params={"type": "credit"}).json()
    assert [(t["type"], t["amount"]) for t in extrato] == [("credit", 250)]


def test_erros_http(client):
    ana = conta(client, "Ana", "12345678901", 100)
    beto = conta(client, "Beto", "10987654321", 0)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/accounts/999").status_code == 404
    assert client.post("/accounts", json={"owner": "X", "document": "1"}).status_code == 422
    assert client.post("/transfers", json={"from_account": ana, "to_account": beto, "amount": 999}).status_code == 409
    assert client.post("/transfers", json={"from_account": ana, "to_account": ana, "amount": 1}).status_code == 422
    assert client.get(f"/accounts/{ana}/statement", params={"type": "pix"}).status_code == 422


def test_50_transferencias_simultaneas_preservam_o_total(client):
    ana = conta(client, "Ana", "12345678901", 2500)
    beto = conta(client, "Beto", "10987654321", 0)

    def go(_):
        return client.post("/transfers", json={"from_account": ana, "to_account": beto, "amount": 100}).status_code

    with ThreadPoolExecutor(max_workers=50) as ex:
        codes = list(ex.map(go, range(50)))
    assert codes.count(200) == 25 and codes.count(409) == 25
    assert client.get(f"/accounts/{ana}").json()["balance"] == 0
    assert client.get(f"/accounts/{beto}").json()["balance"] == 2500
