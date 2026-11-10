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

