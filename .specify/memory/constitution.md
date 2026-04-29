# Polymarket Merge Constitution

## Core Principles

### I. Underdog Value Strategy (NON-NEGOTIABLE)
The bot MUST only bet on underdog outcomes where market price ≤ 35% (MAX_PRICE) and odds ≤ 20:1 (MAX_ODDS).
- Target mispriced underdogs: probability estimates vs market-implied odds
- Reject any bet where AI probability < implied probability × 0.85 (the 85% rule)
- Edge MUST be positive and above minimum threshold (default 5%)

### II. Multi-Stage Market Filtering
Markets pass through 3 sequential filters before analysis:
1. Volume Filter: volume_24h ≥ MIN_VOLUME ($10,000)
2. Live Market Filter: resolution within 48h, exclude politics/future/financial
3. Value Filter: underdog price ≤ MAX_PRICE, odds ≤ MAX_ODDS
- A market MUST pass all three stages to be analyzed

### III. Fault-Tolerant AI Analysis
- 3 agents run concurrently per market (sports, esports, odds analysts)
- Each agent returns: probability, confidence, reasoning
- Average probability across successful agents
- If any agent fails, other agents MUST continue independently
- Failed agents MUST be ignored (not block decision)

### IV. Kelly Criterion Position Sizing
- Stake calculated using Kelly formula: kelly_frac × ((b × p - q) / b) × bankroll
- Where b = odds - 1, p = AI probability, q = 1 - p
- Kelly fraction defaults to 25% (conservative)
- Minimum stake: $1.00 (Polymarket minimum)
- Maximum stake: 10% of current bankroll
- Bankroll MUST never go below 0

### V. Deduplication
- Only one open bet per market_id per trading_mode
- Checked via has_open_bet_for_market() before placing any bet
- Both paper and live modes track open bets independently

## Domain Constraints

### Technology Stack
- Language: Python 3.14
- Database: PostgreSQL (primary persistence)
- Cache: Redis (market data caching)
- LLM Provider: MiniMax (agent inference)
- Framework: Pydantic (data validation and settings)

### Betting Rules
- Bankroll never goes below 0 (position sizing prevents it)
- Bets only placed on unresolved markets
- AI analysis is best-effort; failed agents are ignored
- Edge must be positive and above minimum threshold (5% default)
- Underdog must not be "too unlikely" per AI (85% rule)

### Persistence Requirements
- All bets persisted in PostgreSQL with full audit trail
- Sub-100ms read latency for open bets via Redis cache
- Zero data loss during mode transitions (paper ↔ live)
- Clean architectural separation between paper and live execution paths

## Development Workflow

### Code Review
- All PRs/reviews MUST verify compliance with constitution principles
- Complexity MUST be justified with simpler alternative rejected
- Use docs/domain.md and docs/glossary.md for domain terminology

### Testing
- Unit tests REQUIRED for new agent logic
- Integration tests REQUIRED for repository patterns
- Contract tests REQUIRED for API endpoints
- Test-First (TDD) strongly encouraged for decision logic

### Architecture
- Repository pattern for all database operations
- Event-driven architecture for execution tracking
- Separation: Scanner → Decision Gate → Execution → Resolution

**Version**: 1.0.0 | **Ratified**: TODO | **Last Amended**: 2026-04-28
