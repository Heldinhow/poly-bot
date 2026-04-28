# Polymarket Merge — APIs

## External APIs

### Polymarket Gamma API

**Base URL**: `https://gamma-api.polymarket.com`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/events` | GET | Fetch active markets |
| `/markets/{id}` | GET | Get market details + resolution state |

**Key fields used:**
- `question`, `volume24hr`, `liquidity`, `outcomePrices`, `outcomes`, `closed`, `conditionId`

### MiniMax API

**Base URL**: `https://api.minimax.chat/v1`

**Purpose**: LLM inference for AI agents

**Authentication**: API key via header

**Usage**: Each agent sends a specialized prompt requesting probability estimate, confidence, and reasoning for a specific market.

### Telegram Bot API

**Purpose**: Real-time alerts for new bets and portfolio updates

**Methods used:**
- `send_message` — bet alerts, portfolio updates

**Configuration:**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Internal Interfaces

### BetRepository (`db/repository.py`)

```python
create_bet(bet: Bet) -> int                    # Insert bet, return ID
get_open_bets(mode: str | None) -> list[Bet]   # Load unresolved bets
get_bet_by_market_id(id: str) -> Bet | None     # Single bet lookup
has_open_bet_for_market(id: str, mode: str) -> bool  # Deduplication check
resolve_bet(id: str, won: bool, mode: str) -> bool   # Mark resolved
get_bet_history(mode, resolved, limit) -> list[Bet]  # Filtered query
get_stats(mode: str | None) -> dict              # Aggregated statistics
```

### AgentRepository (`db/agent_repository.py`)

```python
create_agent(...) -> UUID
get_agent_by_id(id) -> dict | None
get_agent_by_name(name) -> dict | None
list_agents(active_only=True) -> list[dict]
update_agent(id, **fields) -> bool
delete_agent(id) -> bool
```

### SkillRepository (`db/skill_repository.py`)

```python
create_skill(name, content, description) -> UUID
get_skill_by_id(id) -> dict | None
list_skills(active_only=True) -> list[dict]
update_skill(id, **fields) -> bool
delete_skill(id) -> bool
```

### ExecutionRepository (`db/execution_repository.py`)

```python
create_log(task_id, market_id, agent_id, runtime, model) -> UUID
claim_log(log_id, runtime) -> bool
start_log(log_id) -> bool
update_log_result(log_id, status, probability, confidence, ...) -> bool
get_log(id) -> dict | None
list_logs(market_id, agent_id, status, limit, offset) -> list[dict]
create_step(...) -> UUID
list_steps(log_id) -> list[dict]
```

### PaperPortfolio (`portfolio.py`)

```python
record_bet(market_id, question, outcome, price, probability_ai, analysis_summary) -> Bet | None
resolve_bet(market_id: str, won: bool) -> None
get_open_bets() -> list[Bet]
stats() -> dict   # bankroll, roi, wins, losses, sharpe, drawdown, etc.
to_dict() -> dict  # Full portfolio state for dashboard
```

### TradingModeGate (`trading/mode_gate.py`)

```python
get_current_mode() -> str    # 'paper' or 'live'
is_live_enabled() -> bool
get_mode_for_bet() -> str    # Mode to tag on new bets
```

### AgentRunner (`agents/runtime/runner.py`)

```python
analyze_market(market_id, question, yes_price, no_price, volume_24h, resolution_date) -> Result | None
# Orchestrates: registry → exec env → runtime manager → tracker → result
```

## Data Patterns

### Bet Creation Flow
```
scanner.py ──▶ portfolio.record_bet() ──▶ BetRepository.create_bet() ──▶ PostgreSQL
```

### Bet Resolution Flow
```
reporter.resolve_portfolio() ──▶ portfolio.resolve_bet() ──▶ BetRepository.resolve_bet() ──▶ PostgreSQL
```

### Portfolio Stats Flow
```
PaperPortfolio.stats() ──▶ BetRepository.get_stats() + get_bet_history()
```

## Dashboard API Endpoints

### Bets

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | Portfolio statistics |
| `/api/bets/open` | GET | Unresolved bets |
| `/api/bets/resolved?limit=50` | GET | Resolved bets |
| `/api/bets/timeseries?days=30` | GET | Daily bankroll replay |

### Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents` | GET | List active agents |
| `/api/agents` | POST | Create agent |
| `/api/agents/:id` | GET | Get agent by ID |
| `/api/agents/:id` | PUT | Update agent |
| `/api/agents/:id` | DELETE | Delete agent |

### Skills

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/skills` | GET | List active skills |
| `/api/skills` | POST | Create skill |
| `/api/skills/:id` | GET | Get skill by ID |
| `/api/skills/:id` | PUT | Update skill |
| `/api/skills/:id` | DELETE | Delete skill |

### Executions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/executions?market_id=&status=&limit=100` | GET | List executions |
| `/api/executions/:id` | GET | Get execution detail |
| `/api/executions/:id/steps` | GET | Get execution steps |

### Scan Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scan/status` | GET | Current scan enabled/disabled state |
| `/api/scan/toggle` | POST | Toggle scan on/off |
| `/api/scan/enable` | POST | Enable scanning |
| `/api/scan/disable` | POST | Disable scanning |

## Authentication

- **Polymarket**: Public API, no auth required for read endpoints
- **MiniMax**: API key via `Authorization` header
- **Telegram**: Bot token via `Bot(token=...)`
- **PostgreSQL**: Connection string with credentials in `DATABASE_URL`
