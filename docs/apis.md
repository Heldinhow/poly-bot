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

## Authentication

- **Polymarket**: Public API, no auth required for read endpoints
- **MiniMax**: API key via `Authorization` header
- **Telegram**: Bot token via `Bot(token=...)`
- **PostgreSQL**: Connection string with credentials in `DATABASE_URL`
