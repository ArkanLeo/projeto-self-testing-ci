import pytest

from src.domain.errors import InsufficientFunds, InvalidAmount, SameAccountTransfer
from src.domain.rules import apply_transfer, validate_amount


def test_transferencia_move_o_valor_entre_saldos():
    assert apply_transfer(1000, 200, 300) == (700, 500)


def test_transferencia_do_saldo_inteiro_zera_origem():
    assert apply_transfer(500, 0, 500) == (0, 500)


def test_saldo_insuficiente_levanta_erro():
    with pytest.raises(InsufficientFunds):
        apply_transfer(100, 0, 101)


@pytest.mark.parametrize("valor", [0, -5, 1.5, "10", None, True])
def test_valor_invalido_e_rejeitado(valor):
    with pytest.raises(InvalidAmount):
        validate_amount(valor)


def test_mesma_conta_nao_pode_transferir_para_si():
    with pytest.raises(SameAccountTransfer):
        apply_transfer(1000, 1000, 10, same_account=True)
