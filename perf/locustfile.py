"""Teste de carga do endpoint de transferência.
Uso: make load   (50 usuários simultâneos, 20s, servidor local)
"""
import random

from locust import HttpUser, between, events, task

ACCOUNTS = []


@events.test_start.add_listener
def prepara_contas(environment, **_):
    import requests
    host = environment.host
    for i in range(10):
        r = requests.post(f"{host}/accounts", json={
            "owner": f"Conta {i}", "document": f"{10000000000 + i}", "initial_balance": 10_000_000})
        ACCOUNTS.append(r.json()["id"])


class Pagador(HttpUser):
    wait_time = between(0.01, 0.1)

    @task
    def transferir(self):
        a, b = random.sample(ACCOUNTS, 2)
        self.client.post("/transfers", json={"from_account": a, "to_account": b, "amount": 100},
                         name="/transfers")
