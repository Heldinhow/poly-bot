# Polymarket Merge — Workflows

## Main Loop Workflow

```
[main.py]
│
├── Initialize components (client, alerts, portfolio, scanner)
│
├── Infinite loop:
│   │
│   ├── scanner.scan()
│   │   │
│   │   ├── Fetch active markets (top 200 by volume)
│   │   │
│   │   ├── Apply 3-stage filters
│   │   │   ├── Volume ≥ MIN_VOLUME
│   │   │   ├── Live market (resolution ≤ 48h)
│   │   │   └── Underdog value (price ≤ MAX_PRICE, odds ≤ MAX_ODDS)
│   │   │
│   │   ├── For each value market:
│   │   │   │
│   │   │   ├── Run 3 AI agents concurrently (async)
│   │   │   │   ├── SportsAnalyst.analyze(market)
│   │   │   │   ├── EsportsAnalyst.analyze(market)
│   │   │   │   └── OddsAnalyst.analyze(market)
│   │   │   │
│   │   │   ├── Average probabilities from successful agents
│   │   │   │
│   │   │   ├── Calculate edge = (ai_prob * odds) - 1.0
│   │   │   │
│   │   │   ├── DecisionGate.evaluate_edge()
│   │   │   │   ├── REJECT if edge < MIN_EDGE
│   │   │   │   ├── REJECT if ai_prob < implied * 0.85
│   │   │   │   └── Classify: HIGH / MEDIUM / LOW
│   │   │   │
│   │   │   ├── If not REJECT:
│   │   │   │   │
│   │   │   │   ├── portfolio.record_bet()
│   │   │   │   │   ├── Check for duplicate open bet
│   │   │   │   │   ├── Calculate Kelly stake
│   │   │   │   │   ├── Create Bet with trading_mode
│   │   │   │   │   ├── BetRepository.create_bet() → PostgreSQL
│   │   │   │   │   └── Deduct stake from bankroll
│   │   │   │   │
│   │   │   │   └── alerts.send_paper_bet() → Telegram
│   │   │   │
│   │   │   └── Log decision
│   │   │
│   │   ├── Resolve closed markets
│   │   │   ├── reporter.resolve_portfolio()
│   │   │   │   ├── For each open bet:
│   │   │   │   │   ├── Check if market closed via API
│   │   │   │   │   ├── Determine winner
│   │   │   │   │   ├── portfolio.resolve_bet()
│   │   │   │   │   │   ├── Update DB record
│   │   │   │   │   │   └── Adjust bankroll
│   │   │   │   │   └── Log result
│   │   │   │   └── Send portfolio update alert
│   │   │   │
│   │   ├── dashboard.write_dashboard() → HTML file
│   │   │
│   │   └── Log portfolio stats
│   │
│   └── Sleep for SCAN_INTERVAL_SECS (default 300s)
│
└── On interrupt: close client, exit
```

## Bet Creation Workflow

```
Trigger: scanner finds a market passing all filters and decision gate

1. Identify underdog outcome (cheaper side)
2. Calculate payout odds = 1.0 / underdog_price
3. Calculate Kelly stake with constraints:
   - Minimum $1.00
   - Maximum 10% bankroll
4. Check for duplicate open bet (same market_id + trading_mode)
5. Create Bet dataclass with trading_mode from TradingModeGate
6. Persist via BetRepository.create_bet() → PostgreSQL
7. Deduct stake from bankroll
8. Send Telegram alert
9. Log bet details
```

## Bet Resolution Workflow

```
Trigger: scanner cycle checks open bets

1. For each open bet in portfolio:
   a. Call Polymarket API for market state
   b. If not closed → skip
   c. Parse outcome prices
   d. Winner = outcome with price closest to 1.0
   e. won = (winner == bet.outcome)
   f. portfolio.resolve_bet(market_id, won)
      - Update DB: resolved=True, result, resolved_at
      - If won: bankroll += payout
   g. Log resolution

2. If any bets resolved:
   a. Generate dashboard
   b. Send portfolio update via Telegram
```

## Startup Workflow

```
1. Load settings from environment (.env)
2. Validate required env vars (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MINIMAX_API_KEY, DATABASE_URL)
3. Normalize TRADING_MODE (paper|live, default paper)
4. Check PostgreSQL connectivity → exit if unreachable
5. Initialize database schema (idempotent)
6. Initialize TradingModeGate
7. Create BetRepository
8. Create PaperPortfolio (loads open bets from DB)
9. Create remaining components (client, scanner, agents, etc.)
10. Log configuration summary
11. Enter main loop
```

## Error Handling Patterns

| Error | Handling |
|-------|----------|
| DB unreachable at startup | Exit with error code 1 |
| DB transient error | Retry 3x with backoff, then raise |
| AI agent failure | Log warning, continue with other agents |
| Polymarket API failure | Log error, skip market |
| Telegram send failure | Log error, continue |
| Invalid TRADING_MODE | Default to 'paper', log warning |
