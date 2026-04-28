# Agent Instructions

## Purpose

This repository contains an autonomous underdog value-betting bot for Polymarket. This `agents.md` guides AI agents working on this codebase.

## Read Docs BEFORE Code

Before scanning the codebase, read the relevant documentation in `/docs/`. This saves tokens and provides context faster than reading source files.

### Track Changes
All project changes are recorded in **`docs/changelog.md`**. Check this file first to understand what has recently changed.

## Doc Selection by Task Type

| Task Type | Read These Docs First |
|-----------|----------------------|
| Feature development | `overview.md`, `architecture.md`, `workflows.md` |
| Bug fixing | `overview.md`, `architecture.md`, `apis.md` |
| Refactoring | `architecture.md`, `conventions.md` |
| API changes | `apis.md`, `domain.md` |
| Database changes | `architecture.md`, `domain.md`, `conventions.md` |
| Adding new agents | `overview.md`, `architecture.md`, `workflows.md` |
| Infrastructure/DevOps | `architecture.md`, `conventions.md` |
| Onboarding | `overview.md`, `architecture.md`, `glossary.md` |

## Quick Reference

### Tech Stack
- Python 3.14
- PostgreSQL 16 + `psycopg2-binary`
- `httpx` for HTTP
- `aiohttp` for API server
- `pydantic-settings` for config
- `python-telegram-bot` for alerts
- MiniMax API for LLM inference
- React 19 + TypeScript + Vite 6 (dashboard frontend)
- Tailwind CSS v4 + TanStack Query + Recharts (dashboard UI)

### Key Entry Points
- `main.py` — Application entry point, main loop
- `scanner.py` — Orchestrates scan → filter → analyze → decide → bet
- `config.py` — All configuration via Pydantic Settings
- `db/schema.sql` — Database schema
- `db/repository.py` — All database operations

### Critical Business Rules
1. Only one open bet per `market_id` per `trading_mode`
2. Edge must be ≥ `MIN_EDGE` (default 5%)
3. AI probability must be ≥ implied * 0.85
4. Kelly fraction default is 25% (conservative)
5. Max stake is 10% of bankroll, min is $1.00
6. `TRADING_MODE` env var controls paper vs live tagging

### Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `TELEGRAM_BOT_TOKEN` | Yes | — | Telegram Bot API token |
| `TELEGRAM_CHAT_ID` | Yes | — | Telegram chat for alerts |
| `MINIMAX_API_KEY` | Yes | — | MiniMax LLM API key |
| `TRADING_MODE` | No | `paper` | `paper` or `live` |
| `INITIAL_BANKROLL` | No | 50.0 | Starting bankroll |
| `KELLY_FRAC` | No | 0.25 | Kelly fraction (0-1) |
| `MIN_EDGE` | No | 0.05 | Minimum edge threshold |
| `API_PORT` | No | 8080 | HTTP API server port |

### Database
- Schema initialized automatically on startup (`init_schema()`)
- Connection pool: min=1, max=5
- All bets stored in `bets` table with `trading_mode` field
- Raw SQL with parameterized queries (no ORM)

### Patterns
- Repository pattern for DB access
- Sync code with async only for concurrent AI agents
- Fail fast on startup if DB unreachable
- Log and continue for recoverable errors

## What NOT to Do
- Do NOT reintroduce CSV persistence — all storage is PostgreSQL
- Do NOT skip `TradingModeGate` — all bets must be tagged
- Do NOT hardcode trading mode — use env var
- Do NOT modify `paper_trades.csv` — it's legacy/read-only

## Documentation Maintenance

**CRITICAL**: Any change to the codebase MUST be reflected in documentation.

### After every change, update:

1. **`docs/changelog.md`** — Add an entry under `[Unreleased]` or create a new version section
   - What was added/changed/removed/fixed
   - Why the change was made (1-2 sentences)
   - Any migration steps required

2. **Relevant `/docs/*.md` files** — Keep docs in sync with code:
   - New feature → update `overview.md`, `architecture.md`, `workflows.md`
   - API change → update `apis.md`
   - Business rule change → update `domain.md`
   - New convention → update `conventions.md`
   - New term → update `glossary.md`

3. **`agents.md`** — Update if any of these change:
   - Environment variables
   - Business rules
   - Tech stack
   - Entry points
   - Critical patterns

### Changelog Format

Follow [Keep a Changelog](https://keepachangelog.com/):

```markdown
## [Unreleased]

### Added
- Feature X — description and reason

### Changed
- Component Y — what changed and why

### Fixed
- Bug Z — root cause summary

### Deprecated
- Old feature — migration path

### Removed
- Dead code — reason for removal
```

When releasing, move `[Unreleased]` to a dated version:
```markdown
## [2.1.0] — 2026-05-15
```

## Testing
- No automated tests exist yet
- Manual verification: run bot, check PostgreSQL for new records
- Migration script: `PYTHONPATH=. python scripts/migrate_csv.py`
