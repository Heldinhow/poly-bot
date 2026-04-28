# Polymarket Merge — Architecture

## System Design

**Type**: Monolith script-based (not microservices)

Single Python process with an infinite loop. All components run in the same memory space. Async is used only for concurrent AI agent calls.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.14 |
| HTTP Client | `httpx` |
| API Server | `aiohttp` |
| Frontend | React 19 + TypeScript + Vite 6 + Tailwind CSS v4 |
| State Management | TanStack Query |
| Charts | Recharts |
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
├── api.py           HTTP API server (aiohttp) — serves JSON + static frontend
├── llm.py           MiniMax API client
├── agents/          AI agent implementations
│   ├── base.py      BaseAgent abstract class
│   ├── sports_analyst.py
│   ├── esports_analyst.py
│   ├── odds_analyst.py
│   ├── registry.py      AgentRegistry (DB-backed market→agent matching)
│   ├── classifier.py    MarketClassifier (keyword-based categorization)
│   ├── tracker.py       ExecutionTracker (stream → DB persistence)
│   ├── circuit_breaker.py  Circuit breaker per runtime
│   └── runtime/         Agent Runtime (Multica-style)
│       ├── models.py        Dataclasses (Message, Result, Session, Task)
│       ├── manager.py       RuntimeManager (auto-detect, execute, fallback)
│       ├── registry.py      BackendRegistry (factory for runtimes)
│       ├── generic_backend.py  Base CLI spawner with configurable parser
│       ├── claude_backend.py   Claude Code integration
│       ├── opencode_backend.py OpenCode integration
│       ├── execenv.py       Isolated workdir preparation
│       ├── prompt_builder.py Task prompt construction
│       ├── version.py       CLI version detection
│       └── runner.py        AgentRunner (orchestrates full pipeline)
├── db/              PostgreSQL layer
│   ├── connection.py      Connection pool + schema init
│   ├── repository.py      BetRepository (CRUD)
│   ├── agent_repository.py
│   ├── skill_repository.py
│   ├── execution_repository.py
│   └── agent_skill_repository.py
├── models/          Data models
│   └── bet.py       Bet dataclass (paper + live)
├── trading/         Trading infrastructure
│   └── mode_gate.py TradingModeGate (env toggle)
└── frontend/        React SPA dashboard (ATLAS v2)
    ├── src/
    │   ├── components/   KPI, Chart, Tables, Header
    │   ├── hooks/        TanStack Query hooks
    │   ├── pages/        AgentsPage, SkillsPage, ExecutionsPage
    │   └── lib/          API client + types
    └── dist/          Production build (served by api.py)
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
                                     ├──▶ AgentRunner ──▶ RuntimeManager
                                     │                       ├──▶ detect installed CLIs
                                     │                       ├──▶ BackendRegistry
                                     │                       │       ├──▶ ClaudeBackend
                                     │                       │       ├──▶ OpencodeBackend
                                     │                       │       └──▶ GenericBackend (extensible)
                                     │                       ├──▶ ExecEnv (isolated workdir)
                                     │                       ├──▶ ExecutionTracker ──▶ execution_logs/steps
                                     │                       └──▶ Result (probability, confidence)
                                     │
                                     ├──▶ agents/*.py (fallback — legacy async concurrent)
                                     │
                                     ├──▶ decision.py
                                     │
                                     ├──▶ portfolio.py ──▶ db/repository.py ──▶ PostgreSQL
                                     │                                              ▲
                                     │                                              │
                                     │         ┌────────────────────────────────────┘
                                     │         │
                                     │    api.py ──▶ React SPA (frontend/dist/)
                                     │         │
                                     └──▶ alerts.py ──▶ Telegram
```

## Important Design Decisions

1. **Sync over async**: Project is fundamentally synchronous. Async is only used for concurrent AI agent calls within the scan cycle.

2. **Repository pattern**: All DB access abstracted behind repositories. Easy to swap storage if needed.

3. **Raw SQL over ORM**: Small schema, explicit control. `psycopg2` with parameterized queries.

4. **Env-based mode switching**: `TRADING_MODE=paper|live` controls behavior without code changes.

5. **Connection pooling**: `psycopg2.pool.SimpleConnectionPool` with min=1, max=5.

6. **Schema init on startup**: `init_schema()` runs automatically when `main.py` starts. Idempotent.

7. **Agent Runtime (Multica-style)**: Coding agents execute in isolated workdirs with auto-detected CLIs. The scanner delegates to `AgentRunner`, which orchestrates the full pipeline. Fallback to legacy agents when runtime fails.

8. **Vendor-neutral runtimes**: Auto-detect all installed agent CLIs (Claude Code, OpenCode, Hermes, Codex, Gemini, Pi, Cursor, Kimi, Kiro, OpenClaw). No hardcoded runtime list.

9. **Task-per-market**: Each market becomes an isolated task with its own workdir, context files, and execution log.

10. **Tracking mandatory**: 100% of executions log steps to `execution_steps`. No tracking, no observability.

11. **Circuit breaker**: Per-runtime circuit breaker prevents cascading failures (3 failures → 5min cooldown).

12. **Skills as markdown**: Skills are markdown files injected into the agent's workdir `.skills/` directory. Editable via dashboard.
