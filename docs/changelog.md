# Polymarket Merge — Changelog

## [2.0.0] — Persistence & Trading Mode

### Added
- **PostgreSQL persistence** — All bets stored in PostgreSQL with ACID guarantees
- **Database schema** — `bets` table with full audit trail, indexes, and constraints
- **Bet dataclass** — Unified model for both paper and live bets with `trading_mode` field
- **BetRepository** — Repository pattern for all bet CRUD operations
- **TradingModeGate** — Environment-based switching between `paper` and `live` modes
- **Connection pooling** — `psycopg2` pool for efficient DB connections
- **CSV migration script** — One-time `scripts/migrate_csv.py` for legacy data
- **Docker Compose** — `docker-compose.yml` with PostgreSQL 16
- **Documentation** — Complete `/docs` folder with system documentation

### Changed
- **`portfolio.py`** — Refactored to use `BetRepository` instead of CSV
- **`config.py`** — Added `DATABASE_URL`, `TRADING_MODE` settings
- **`main.py`** — Initializes DB schema on startup, wires new components
- **`alerts.py`** — Updated to use `Bet` model instead of `PaperBet`
- **`requirements.txt`** — Added `psycopg2-binary`
- **`.env.example`** — Added `DATABASE_URL` and `TRADING_MODE`

### Removed
- **CSV persistence** — No more writes to `paper_trades.csv`
- **PaperBet dataclass** — Replaced by unified `Bet` model

### Migration
- Legacy CSV data migrated to PostgreSQL with `trading_mode='paper'`
- Migration is idempotent — safe to run multiple times

## [1.0.0] — Initial Release

### Features
- Paper trading bot for Polymarket
- 3 AI agents (Sports, Esports, Odds Analyst)
- Kelly Criterion position sizing
- 3-stage market filtering
- Telegram alerts
- Static HTML dashboard
- CSV persistence
