# Polymarket Merge — Conventions

## Coding Patterns

### Configuration
- All configuration via Pydantic `BaseSettings` in `config.py`
- Environment variables loaded from `.env` file
- Singleton pattern via `@lru_cache` on `get_settings()`

### Database Access
- **Repository pattern**: All DB operations through `BetRepository`
- **Connection pooling**: `psycopg2.pool.SimpleConnectionPool` in `db/connection.py`
- **Context managers**: `get_db_connection()` and `get_db_cursor()` for safe resource handling
- **Parameterized queries**: All SQL uses `%s` placeholders (SQL injection safe)

### Async Usage
- **Sync-first**: Main code is synchronous
- **Async only for AI agents**: `asyncio.new_event_loop()` created per scan cycle for concurrent agent calls
- **Event loop cleanup**: Always close loop in `finally` block

### Error Handling
- **Fail fast on startup**: DB unreachable → immediate exit
- **Graceful degradation**: Redis unavailable → bypass cache (pattern ready for future)
- **Log and continue**: Single market/agent failure should not stop the scan

### Logging
- Module-level loggers: `logging.getLogger(__name__)`
- Format: `"%(asctime)s [%(levelname)s] %(name)s: %(message)s"`
- INFO level for operational events
- WARNING for recoverable issues (agent failures, API hiccups)
- ERROR for serious problems

## Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Classes | PascalCase | `BetRepository`, `TradingModeGate` |
| Functions | snake_case | `get_settings()`, `create_bet()` |
| Constants | UPPER_SNAKE | `MIN_VOLUME`, `MAX_PRICE` |
| Private methods | _leading_underscore | `_load_csv()`, `_kelly_stake()` |
| Env vars | UPPER_SNAKE | `DATABASE_URL`, `TRADING_MODE` |
| DB columns | snake_case | `market_id`, `trading_mode` |

## Folder Structure

```
├── main.py              # Entry point
├── config.py            # Settings
├── client.py            # Polymarket API client
├── scanner.py           # Main orchestrator
├── filters.py           # Market filtering
├── decision.py          # Decision gate
├── portfolio.py         # Bankroll + bet management
├── reporter.py          # Market resolution
├── alerts.py            # Telegram notifications
├── api.py               # HTTP API server (aiohttp) — serves JSON + static files
├── llm.py               # LLM client
├── requirements.txt     # Dependencies
├── docker-compose.yml   # PostgreSQL container
├── .env                 # Environment variables
├── .env.example         # Template
│
├── agents/              # AI agents
│   ├── __init__.py      # Factory
│   ├── base.py          # Abstract base
│   ├── sports_analyst.py
│   ├── esports_analyst.py
│   └── odds_analyst.py
│
├── db/                  # Database layer
│   ├── __init__.py
│   ├── schema.sql       # PostgreSQL schema
│   └── connection.py    # Connection pool
│
├── models/              # Data models
│   ├── __init__.py
│   └── bet.py           # Bet dataclass
│
├── trading/             # Trading infrastructure
│   ├── __init__.py
│   └── mode_gate.py     # Mode switching
│
├── scripts/             # Utility scripts
│   └── migrate_csv.py   # CSV → PostgreSQL migration
│
└── frontend/            # React SPA dashboard (ATLAS v2)
    ├── src/
    │   ├── components/  # React components
    │   ├── hooks/       # TanStack Query hooks
    │   ├── lib/         # API client + types
    │   └── styles/      # Global CSS + theme
    └── dist/            # Production build (served by api.py)
```

## Data Models

- **Dataclasses** for in-memory objects (`Bet`, `Market`, `MarketOutcome`)
- **Dict serialization** for DB insertion (`to_db_dict()`)
- **Factory methods** for parsing different sources (`from_db_row()`, `from_csv_row()`)

## Import Order

```python
# 1. Standard library
import logging
from datetime import datetime

# 2. Third-party
import httpx
from pydantic_settings import BaseSettings

# 3. Local modules (absolute imports)
from config import get_settings
from models.bet import Bet
```

## Documentation Conventions

### Every Code Change Requires Doc Updates

**Rule**: If you change code, you must update documentation. No exceptions.

### What to update by change type:

| Change Type | Update These Files |
|-------------|-------------------|
| New feature | `docs/overview.md`, `docs/architecture.md`, `docs/workflows.md` |
| Bug fix | `docs/changelog.md` (Fixed section) |
| Refactoring | `docs/architecture.md`, `docs/conventions.md` |
| API endpoint change | `docs/apis.md` |
| Business rule change | `docs/domain.md`, `docs/changelog.md` |
| New env var | `agents.md`, `docs/changelog.md` |
| New dependency | `agents.md`, `docs/architecture.md` |
| Database schema change | `docs/domain.md`, `docs/changelog.md` |

### Changelog Rules

- **Always** add an entry to `docs/changelog.md` under `[Unreleased]`
- Use categories: `Added`, `Changed`, `Fixed`, `Deprecated`, `Removed`
- Include **why** the change was made, not just what
- Link to relevant docs when applicable
- Create a new version header when releasing

### agents.md Rules

- **Must** update `agents.md` when:
  - Environment variables change
  - Business rules change
  - Tech stack changes
  - Entry points change
  - Critical patterns change
- Keep the "Doc Selection by Task Type" table accurate

### Doc Quality

- Be concise — optimize for token efficiency
- Use tables for structured data
- Use code blocks for examples
- Cross-reference related docs
- Never leave sections empty — make a reasonable assumption and document it

## Testing Strategy (Future)

- Unit tests for `DecisionGate`, `KellyCriterion` math
- Integration tests for `BetRepository` with test DB
- Mock Polymarket API responses for scanner tests
- Mock Telegram bot for alert tests
