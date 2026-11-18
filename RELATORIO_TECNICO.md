# Relatório Técnico — Wallet API

API REST de carteira digital (contas, transferências, extrato) feita em **Python / FastAPI**, com testes em **PyTest**, CI no **GitHub Actions** e teste de carga com **Locust**.

## 1. Requisitos (SRS)

### Funcionais
| ID | Requisito |
|----|-----------|
| RF01 | Criar conta com titular, documento e saldo inicial (≥ 0). O documento passa por validação cadastral. |
| RF02 | Consultar uma conta pelo id. |
| RF03 | Transferir valor entre duas contas distintas. Valor é inteiro positivo em centavos. |
| RF04 | Rejeitar transferência com saldo insuficiente, sem alterar nenhum saldo. |
| RF05 | Idempotência: a mesma `Idempotency-Key` não gera uma segunda cobrança; devolve a resposta original (`replayed: true`). |
| RF06 | Consultar extrato com filtro por tipo (`debit`/`credit`) e por período (`date_from`, `date_to`, formato AAAA-MM-DD). |
| RF07 | Notificar o serviço anti-fraude (webhook) a cada transferência concluída. |

### Não funcionais
| ID | Requisito |
|----|-----------|
| RNF01 | Consistência: concorrência nunca pode gerar saldo negativo nem criar/perder dinheiro. |
| RNF02 | Falha ou lentidão do anti-fraude não pode desfazer nem travar transferências. |
| RNF03 | Valores monetários em inteiros (centavos), sem ponto flutuante. |
| RNF04 | Cobertura de testes ≥ 85% (linhas) e ≥ 80% (branches), validada no CI. |
| RNF05 | Suportar 50 requisições simultâneas em `/transfers` sem erros. |
| RNF06 | Erros de negócio retornam JSON `{"error": ...}` com status HTTP adequado (404, 409, 422). |

## 2. Arquitetura

```
controllers (FastAPI)  ->  services (WalletService)  ->  repositories (SQLite)
                                  |                  
                          domain (regras puras + erros)
                                  |
                          gateways (anti-fraude, cadastro)
```

- **domain**: regras de transferência sem I/O, ideais para TDD.
- **services**: orquestra regras, repositórios e gateways. A transferência roda dentro de um lock + transação (`commit`/`rollback`); a notificação ao anti-fraude acontece **depois** e fora do lock (RNF02).
- **repositories**: SQLite (em memória nos testes e por padrão).
- **gateways**: interfaces injetadas, o que permite trocar por Mock/Stub nos testes.

Decisão sobre concorrência: uma conexão SQLite compartilhada protegida por `RLock`. É simples e correta para este escopo; em produção o caminho natural seria PostgreSQL com `SELECT ... FOR UPDATE`.

## 3. Estratégia de branching

**Trunk-Based Development**: `main` é sempre estável, as branches são curtas (`feat/*`, `test/*`, `hotfix/*`) e entram via Pull Request com o CI verde. Nada vai direto para a `main`. Commits seguem **Conventional Commits** (`feat:`, `test:`, `fix:`, `refactor:`, `ci:`, `docs:`). Dois hotfixes documentados no histórico:

1. `hotfix/extrato-filtro-data` — o filtro `date_to` excluía transações do último dia.
2. `hotfix/idempotencia-concorrente` — chave de idempotência era checada fora do lock e duas requisições simultâneas podiam passar.

Dica para ver: `git log --graph --oneline`.

## 4. Pirâmide de testes

| Nível | Pasta | O que cobre |
|-------|-------|-------------|
| Unitário (TDD) | `tests/unit` | Regras puras de transferência e validação de valor. |
| Integração | `tests/integration` | Service + SQLite em memória; **Mock** do anti-fraude (`assert_called_once_with`, `assert_not_called`, `call_count`); **Stub** de validação cadastral (respostas fixas). |
| E2E | `tests/e2e` | Fluxo HTTP real (TestClient): criar contas → transferir → extrato; erros HTTP; 50 transferências paralelas. |

**Mock vs Stub:** o Mock verifica a *saída* (o anti-fraude foi chamado, quantas vezes, com quais parâmetros). O Stub só *alimenta* o teste com dados fixos (o `RegistryStub` decide se o documento é válido).

**TDD:** os commits do histórico seguem `test:` (red, falhando) → `feat:` (green) → `refactor:`.

### Cobertura (última execução local)
- Linhas/statements: **99,6%** (meta 85%)
- Branches: **97,2%** (meta 80%)
- 30 testes passando.

## 5. Pipeline de CI (`.github/workflows/ci.yml`)

Dispara em `push` (main, develop) e `pull_request` (para main). Passos: instalar dependências → lint (ruff) → unitários e integração → E2E + **coverage gate** (falha abaixo de 85% de linhas ou 80% de branches) → upload de `htmlcov/`, `coverage.xml` e logs como artefato.

Para bloquear merge quando o CI quebra: em *Settings → Branches → Branch protection rule* na `main`, marcar **Require status checks to pass** (job `test`) e **Require a pull request before merging**. Essa é uma configuração do GitHub, não do arquivo YAML.

## 6. Teste de carga (Locust)

`perf/locustfile.py`: 50 usuários simultâneos, 20 s, `POST /transfers` entre 10 contas (saldo alto, para medir o caminho feliz). Rodar com `make run` e, em outro terminal, `make load`.

| Métrica | Resultado |
|---------|-----------|
| Requisições | 15.608 |
| Falhas | 0 (0%) |
| Latência média | 5,4 ms |
| Mediana / p95 / p99 | 4 ms / 13 ms / 22 ms |
| Máxima | 50 ms |
| Vazão | ~820 req/s |

Sem travamentos nem erros. Observação: ao final, o Locust imprime um erro de fechamento do arquivo CSV; é um bug conhecido da ferramenta ao encerrar, que não afeta as métricas. O teste foi feito em máquina local, com SQLite em memória; números em produção serão diferentes.

## 7. Como rodar

```bash
make install   # dependências
make lint
make test
make cov       # testes + cobertura + gate
make run       # sobe a API em :8000
make load      # teste de carga (API precisa estar no ar)
```
