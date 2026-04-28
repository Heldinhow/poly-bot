# Polymarket Merge — Overview

## Purpose

Autonomous underdog value-betting bot for Polymarket prediction markets. Uses multiple AI agents to estimate true probabilities, compares against market-implied odds, and places bets on mispriced underdogs using Kelly Criterion position sizing.

## Main Features

- **AI-Powered Analysis**: 3 specialized agents (Sports, Esports, Odds) analyze markets concurrently
- **Underdog Value Detection**: Identifies markets where the underdog is mispriced by the market
- **Kelly Criterion Sizing**: Fractional Kelly (default 25%) for position sizing
- **Paper Trading**: Full simulation mode with virtual bankroll tracking
- **Live Trading Ready**: Infrastructure supports switching to live via environment variable
- **PostgreSQL Persistence**: All bets stored with ACID guarantees
- **Telegram Alerts**: Real-time notifications for new bets and portfolio updates
- **ATLAS Dashboard v2**: React 19 + TypeScript SPA with dark mode, real-time data polling (5s), Recharts performance chart, and responsive design — zero mock data

## Target Users

- Single operator running the bot locally
- Future: multi-instance deployment with shared database

## High-Level Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Scan    │───▶│  Filter  │───▶│  Agents  │───▶│ Decision │
│ Markets  │    │ (3-stage)│    │  (3 AI)  │    │   Gate   │
└──────────┘    └──────────┘    └──────────┘    └────┬─────┘
                                                      │
                           ┌──────────────────────────┘
                           ▼
                    ┌──────────────┐      ┌──────────────┐
                    │  Bet Record  │◀────▶│   API Server │
                    │ (PostgreSQL) │      │   (aiohttp)  │
                    └──────────────┘      └──────┬───────┘
                                                  │
                                           ┌──────▼───────┐
                                           │ ATLAS Dashboard│
                                           │ (React SPA)   │
                                           └───────────────┘
```

1. **Scan**: Fetch active markets from Polymarket Gamma API (top 200 by volume)
2. **Filter**: 3-stage filter (volume → live markets → underdog value)
3. **Analyze**: 3 AI agents estimate true probability in parallel
4. **Decide**: Calculate edge, reject if below threshold or AI contradicts market
5. **Record**: Persist bet to PostgreSQL with `trading_mode` tag
6. **Resolve**: Check closed markets, update results, recalculate bankroll

## Trading Modes

| Mode | Description |
|------|-------------|
| `paper` | Simulated bets, no blockchain interaction (default) |
| `live` | Tags bets as live in DB, but blockchain execution not yet implemented |

Switch modes via `TRADING_MODE` environment variable.

## Key Metrics Tracked

- Bankroll and ROI
- Win/loss ratio
- Sharpe ratio
- Maximum drawdown
- Underdog hit rate
- AI bet count
