# Polymarket Merge — Changelog

## [Unreleased]

### Fixed
- **Decision Gate — no bets placed since multi-agent refactor** — `evaluate_edge()` returned `"HIGH"`/`"MEDIUM"`/`"LOW"`, but `scanner.py` checked for `"ACCEPT"`. The mismatch meant `decision == "ACCEPT"` was always false, so `record_bet()` was never called and zero bets were recorded. Fixed by making `evaluate_edge()` return `"ACCEPT"` for valid edges (≥ 5%) and `"REJECT"` for everything else.
- **Audit API — empty dashboard** — `/api/audit/summary` returned a raw array instead of `{ items, next_cursor }`, and `/api/audit/market` used `"factors"` instead of `"decision_factors"`, both mismatched the frontend contract.
- **Audit persistence — FK violation** — `scanner.py` used a placeholder UUID `"00000000-0000-0000-0000-000000000000"` for missing `execution_log_id`, violating the FK constraint on `decision_factors` and `execution_summary`. Changed to pass `None` (NULL) when no execution log exists.

### Added
- **Agent Runtime (Multica-style)** — Coding agents execute in isolated workdirs with real-time tracking
  - `RuntimeManager` auto-detects installed agent CLIs (Claude Code, OpenCode, Hermes, Codex, Gemini, Pi, Cursor, Kimi, Kiro, OpenClaw)
  - `BackendRegistry` factory allows adding new runtimes dynamically
  - `GenericBackend` base class with configurable CLI parser
  - `ClaudeBackend` and `OpencodeBackend` implementations
  - `ExecutionEnvironment` prepares isolated workdirs with AGENTS.md, SOUL.md, COMMANDS.md, and `.skills/`
  - `AgentRunner` orchestrates the full pipeline: registry → workdir → backend → tracker → result
  - Task lifecycle: `enqueue → claim → start → running → complete/fail`
  - Fallback to legacy agents when runtime fails
- **Execution Tracking** — 100% of agent executions are traceable step-by-step
  - `ExecutionTracker` consumes message streams and persists to DB in real-time
  - `execution_logs` table with status pipeline, timing, result, token usage
  - `execution_steps` table with granular tracking (text, thinking, tool_use, tool_result, error, status)
- **Agent Registry + Classifier** — DB-backed agent selection and market categorization
  - `AgentRegistry` selects agents based on keyword matching in market questions
  - `MarketClassifier` categorizes markets (weather, commodity, sports, esports, politics, crypto, tech)
  - Supports ensemble mode when multiple agents match
- **Circuit Breaker** — Per-runtime resilience (3 consecutive failures → 5min cooldown)
- **Skills System** — Markdown skills injected into agent context
  - `skills` table with CRUD operations
  - `agent_skills` junction table for many-to-many relationships
  - Default skills: `weather_skill.md`, `commodity_skill.md`, `news_search_skill.md`
  - Seed script: `scripts/seed_skills.py`
- **Dashboard — Agents, Skills, Executions tabs**
  - `AgentsPage` — CRUD for agents (name, runtime, model, system prompt, skills)
  - `SkillsPage` — CRUD for skills (name, description, markdown content)
  - `ExecutionsPage` — Monitor agent executions with step-by-step timeline
  - `useAgents`, `useSkills`, `useExecutions` hooks with TanStack Query
- **New API Endpoints**
  - `/api/agents` — CRUD agents
  - `/api/skills` — CRUD skills
  - `/api/executions` — List and detail executions with steps
- **New Database Tables**
  - `agents` — agent configuration
  - `skills` — skill content
  - `agent_skills` — agent-skill relationships
  - `execution_logs` — execution tracking
  - `execution_steps` — granular step tracking
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

### Fixed
- **Dashboard — Missing Tailwind theme tokens** — `accent-cyan`, `surface-elevated`, `surface-hover` were used in components but not defined in `@theme` block of `globals.css`, making buttons (New Agent, Create, Save) and card backgrounds invisible
- **Agent/Execution CRUD — JSONB serialization** — psycopg2 cannot adapt Python `dict`/`list` to PostgreSQL `JSONB` natively; wrapped `custom_env`, `sources`, and `tool_input` with `psycopg2.extras.Json()` in `agent_repository.py` and `execution_repository.py`

### Changed
- **Scan control** — DB-backed enable/disable with dashboard toggle and API endpoints
  - `scan_settings` table (single-row config) persists state across restarts
  - `ScanController` loads from DB, falls back to `SCAN_ENABLED` env var on first boot
  - `ScanRepository` for DB CRUD operations
  - `main.py` scanner loop checks `ScanController.is_enabled()` before each scan
  - Dashboard header shows "All Systems Nominal" / "Scan Paused" with Pause/Resume button
  - API endpoints: `GET /api/scan/status`, `POST /api/scan/toggle`, `POST /api/scan/enable`, `POST /api/scan/disable`
  - `SCAN_ENABLED` env var controls default; DB value takes precedence after first toggle

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
