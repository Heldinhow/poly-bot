# Polymarket Merge — Project Vision

## What is this?

Autonomous underdog value-betting bot for Polymarket. Uses multiple AI agents (sports, esports, odds analysts) to estimate true probabilities, compares against market-implied odds, and bets on mispriced underdogs using Kelly Criterion sizing.

## Current State

- **Language**: Python 3.14
- **Mode**: Paper trading only (simulated bets)
- **Persistence**: CSV file (`paper_trades.csv`)
- **Cache**: None (in-memory sets only)
- **Notifications**: Telegram Bot
- **Dashboard**: Static HTML generated locally
- **Tests**: None

## Goals

1. Replace CSV persistence with PostgreSQL for all bets (paper + live)
2. Add Redis caching layer for market data and repeated lookups
3. Introduce trading mode field (paper vs live) in data model
4. Enable mode switching via environment variable
5. Lay the groundwork for live trading integration

## Success Metrics

- All bets persisted in PostgreSQL with full audit trail
- Sub-100ms read latency for open bets via Redis cache
- Zero data loss during mode transitions
- Clean architectural separation between paper and live execution paths

## Constraints

- Keep existing bot behavior unchanged in paper mode
- Minimize downtime during migration from CSV
- No live trading implementation yet — only infrastructure readiness
