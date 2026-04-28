# Polymarket Merge — Architecture

## System Design

**Type**: Monolith script-based (not microservices)

Single Python process with an infinite loop. All components run in the same memory space. Async is used only for concurrent AI agent calls.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.14 |
| HTTP Client | `httpx` |
| Config | `pydantic-settings` + `.env` |
| Database | PostgreSQL 16 + `psycopg2-binary` |
| Notifications | `python-telegram-bot` |
| LLM | MiniMax API |

## Module Map

```
main.py              Entry point, infinite loop
├── config.py        Pydantic Settings, env vars
├── client.py        Polymarket Gamma API client
├── scanner.py       Orchestrator: scan → filter → analyze → decide → bet
├── filters.py       Market filtering predicates
├── decision.py      Decision Gate: edge evaluation
├── portfolio.py     PaperPortfolio: bankroll + Kelly + DB persistence
├── reporter.py      MarketResolver: check closed markets
├── alerts.py        Telegram Bot alerts
├── dashboard.py     HTML dashboard generation
├── llm.py           MiniMax API client
├── agents/          AI agent implementations
│   ├── base.py      BaseAgent abstract class
│   ├── sports_analyst.py
│   ├── esports_analyst.py
│   └── odds_analyst.py
├── db/              PostgreSQL layer
│   ├── connection.py   Connection pool + schema init
│   └── repository.py   BetRepository (CRUD)
├── models/          Data models
│   └── bet.py       Bet dataclass (paper + live)
└── trading/         Trading infrastructure
    └── mode_gate.py TradingModeGate (env toggle)
```

## Key Components

### Scanner (`scanner.py`)
Orchestrates the entire betting pipeline. Runs synchronously but creates an asyncio event loop for concurrent AI agent execution.

### PaperPortfolio (`portfolio.py`)
Manages bankroll, calculates Kelly stakes, and persists bets via `BetRepository`. Zero CSV — all storage is PostgreSQL.

### BetRepository (`db/repository.py`)
Repository pattern abstraction over PostgreSQL. All bet CRUD operations go through here.

### Decision Gate (`decision.py`)
Evaluates whether a bet should be placed based on edge calculation and AI probability vs market-implied probability.

### TradingModeGate (`trading/mode_gate.py`)
Reads `TRADING_MODE` env var and provides mode information. Safety gate for future live trading.

## Data Flow

```
Polymarket API ──▶ client.py ──▶ scanner.py
                                    │
                                    ├──▶ filters.py ──▶ value markets
                                    │
                                    ├──▶ agents/*.py (async concurrent)
                                    │
                                    ├──▶ decision.py
                                    │
                                    ├──▶ portfolio.py ──▶ db/repository.py ──▶ PostgreSQL
                                    │
                                    └──▶ alerts.py ──▶ Telegram
```

## Important Design Decisions

1. **Sync over async**: Project is fundamentally synchronous. Async is only used for concurrent AI agent calls within the scan cycle.

2. **Repository pattern**: All DB access abstracted behind `BetRepository`. Easy to swap storage if needed.

3. **Raw SQL over ORM**: Small schema, explicit control. `psycopg2` with parameterized queries.

4. **Env-based mode switching**: `TRADING_MODE=paper|live` controls behavior without code changes.

5. **Connection pooling**: `psycopg2.pool.SimpleConnectionPool` with min=1, max=5.

6. **Schema init on startup**: `init_schema()` runs automatically when `main.py` starts. Idempotent.
