# Polymarket Merge — Changelog

## [Unreleased]

### Added
- **ATLAS Dashboard v2** — Modern React + TypeScript + Tailwind CSS v4 SPA
  - Vite 6 build system with hot reload
  - React 19 with TypeScript strict mode
  - TanStack Query for auto-refreshing data (5s polling)
  - Recharts for portfolio performance charting
  - Dark mode ATLAS theme with cyan accent (#00e5ff)
  - Responsive design (mobile → tablet → desktop)
  - KPI Cards with staggered fade-up animations
  - Performance Chart with time range selector (7D/30D/90D/ALL)
  - Open Positions table with PAPER/LIVE badges
  - Resolved Bets table with WIN/LOSS badges and P&L
  - Dashboard header with live UTC clock and status indicator
  - Real-time data from PostgreSQL via aiohttp API — zero mock data
  - **PRISM Regime Panel** — 5-regime market analysis (Recovery, Crisis, Bull, Rate Tightening, Euphoria) with animated confidence bars
  - **JANUS Superinvestor Weights** — Agent weight distribution cards with accuracy and trade counts
  - **Agent Hierarchy** — 4-layer architecture visualization (Macro → Sector → Superinvestor → Decision)
  - **CSV Export** — Download stats and bets as CSV files
  - Enhanced animations: fade-up, scale-in, slide-in-right, pulse-glow, shimmer
  - Noise texture overlay and ambient cyan glow effects
  - Custom scrollbar styling
- **HTTP API Server** (`api.py`) — `aiohttp` dashboard API serving real betting data from PostgreSQL
  - `GET /api/stats` — portfolio statistics (bankroll, ROI, Sharpe, drawdown, etc.)
  - `GET /api/bets/open` — unresolved bets
  - `GET /api/bets/resolved?limit=50` — resolved bets ordered by `resolved_at DESC`
  - `GET /api/bets/timeseries?days=30` — daily bankroll replay for charting
  - `GET /{path:.*}` — static file serving from `frontend/dist/` with SPA fallback
  - CORS enabled for all origins
  - Runs concurrently with the scanner in a background daemon thread
- **`Bet.to_dict()`** — JSON serialization for API responses
- **`Bet.id`** — optional DB primary key exposed on model
- **`api_port`** setting in `config.py` (default 8080)
- **`aiohttp>=3.11.0`** dependency in `requirements.txt`

### Changed
- **`main.py`** — starts API server after `PaperPortfolio` initialization and before the scan loop

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
