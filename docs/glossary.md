# Polymarket Merge — Glossary

## Betting Terms

| Term | Definition |
|------|------------|
| **Underdog** | The outcome with lower probability / higher odds. Target of the bot's value strategy. |
| **Edge** | Expected return above fair value: `(true_probability * odds) - 1.0`. Positive edge means the bet is +EV. |
| **Implied Probability** | The market's estimate of probability, derived from price: `1.0 / odds`. |
| **Kelly Criterion** | Mathematical formula for optimal bet sizing based on edge and bankroll. |
| **Kelly Fraction** | Percentage of full Kelly used (default 25% = conservative). |
| **Stake** | Amount wagered on a bet. |
| **Payout** | Potential return if bet wins: `stake * odds`. |
| **ROI** | Return on Investment: `(current_bankroll - initial) / initial * 100`. |
| **Sharpe Ratio** | Risk-adjusted return: `avg_return / std_deviation`. |
| **Drawdown** | Peak-to-trough decline in bankroll. |

## Trading Modes

| Term | Definition |
|------|------------|
| **Paper Trading** | Simulated betting with virtual money. No real money at risk. |
| **Live Trading** | Real betting with actual funds on the blockchain. |
| **Trading Mode** | `paper` or `live` — controlled via `TRADING_MODE` env var. |

## System Terms

| Term | Definition |
|------|------------|
| **Scanner** | The component that periodically fetches and analyzes markets. |
| **Decision Gate** | Filter that evaluates whether a bet has sufficient edge to be placed. |
| **Agent** | AI model specialized in a domain (sports, esports, odds). |
| **Market** | A prediction market on Polymarket with a question and outcomes. |
| **Resolution** | When a market closes and the correct outcome is determined. |
| **Repository** | Pattern that abstracts database operations. |
| **Connection Pool** | Reusable database connections for performance. |

## Tech Terms

| Term | Definition |
|------|------------|
| **Gamma API** | Polymarket's public API for market data. |
| **CTF Exchange** | Polymarket's on-chain exchange for trading outcome tokens. |
| **MiniMax** | LLM provider used for AI agent inference. |
| **Pydantic** | Python library for data validation and settings management. |
| **psycopg2** | PostgreSQL adapter for Python. |
| **ACID** | Atomicity, Consistency, Isolation, Durability — database transaction guarantees. |

## Abbreviations

| Abbreviation | Meaning |
|-------------|---------|
| **EV** | Expected Value |
| **DB** | Database |
| **API** | Application Programming Interface |
| **LLM** | Large Language Model |
| **TTL** | Time To Live (cache expiration) |
| **PK** | Primary Key |
| **UTC** | Coordinated Universal Time |
