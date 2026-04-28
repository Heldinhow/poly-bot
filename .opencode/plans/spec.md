# Persistence & Trading Mode Specification

## Problem Statement

The bot currently stores all bets in a CSV file (`paper_trades.csv`) with no schema enforcement, no concurrency safety, and no distinction between simulated and real trades. This blocks analytics, auditing, and the path to live trading. We need a robust persistence layer with PostgreSQL, a Redis cache, and an explicit trading mode flag.

## Goals

- [ ] All bets (paper and live) persisted in PostgreSQL with ACID guarantees
- [ ] Redis cache for market data and frequently accessed bet state
- [ ] Explicit `trading_mode` field on every bet record
- [ ] Mode switchable via environment variable (`TRADING_MODE=paper|live`)
- [ ] Zero data loss migration from existing CSV
- [ ] Existing paper trading behavior preserved identically

## Out of Scope

- Live trade execution on blockchain (Milestone 3)
- Wallet/private key management
- Circuit breakers and risk limits
- Real-time WebSocket feeds
- Multi-instance bot deployment

---

## User Stories

### P1: PostgreSQL Persistence ⭐ MVP

**User Story**: As a bot operator, I want all bets stored in PostgreSQL so that I can query, audit, and analyze performance reliably.

**Why P1**: CSV is not a database. It prevents any serious analytics and has no concurrency safety.

**Acceptance Criteria**:

1. WHEN a new bet is placed THEN the system SHALL persist it to PostgreSQL within 50ms
2. WHEN a bet is resolved THEN the system SHALL update the record in PostgreSQL with result and resolved_at timestamp
3. WHEN the bot starts THEN the system SHALL load open bets from PostgreSQL (not CSV)
4. WHEN querying bet history THEN the system SHALL support filtering by date range, outcome, and trading_mode
5. WHEN the PostgreSQL connection fails THEN the system SHALL log the error and fail fast (no silent CSV fallback)

**Independent Test**: Start bot with PostgreSQL configured, place a paper bet, query DB directly — record exists with all fields.

---

### P1: Trading Mode Field ⭐ MVP

**User Story**: As a bot operator, I want every bet tagged as either `paper` or `live` so that I can distinguish simulations from real trades.

**Why P1**: Required for safe live trading transition and for accurate performance tracking.

**Acceptance Criteria**:

1. WHEN a bet is created THEN the system SHALL set `trading_mode` based on current `TRADING_MODE` env var
2. WHEN querying bets THEN the system SHALL return the `trading_mode` field for every record
3. WHEN migrating existing CSV bets THEN the system SHALL set `trading_mode='paper'` for all historical records
4. WHEN `TRADING_MODE=live` is set THEN the system SHALL still record bets but tag them as `live`

**Independent Test**: Query bets table — each row has `trading_mode` populated correctly.

---

### P1: ENV-Based Mode Switching ⭐ MVP

**User Story**: As a bot operator, I want to switch between paper and live trading via an environment variable so that I can control risk without code changes.

**Why P1**: Essential for operational safety — live trading must be an explicit, environment-level decision.

**Acceptance Criteria**:

1. WHEN `TRADING_MODE=paper` is set THEN the system SHALL run in paper trading mode (no blockchain interaction)
2. WHEN `TRADING_MODE=live` is set THEN the system SHALL tag new bets as live but still not execute on-chain (infrastructure only)
3. WHEN `TRADING_MODE` is unset or invalid THEN the system SHALL default to `paper` and log a warning
4. WHEN the bot starts THEN the system SHALL log the active trading mode prominently

**Independent Test**: Change TRADING_MODE env var, restart bot, verify logged mode and bet tags.

---

### P2: Redis Cache

**User Story**: As a bot operator, I want frequently accessed data cached in Redis so that the bot is more responsive and reduces redundant work.

**Why P2**: Improves performance but not strictly required for MVP. CSV replacement is higher priority.

**Acceptance Criteria**:

1. WHEN market data is fetched THEN the system SHALL cache it in Redis with a TTL of 60 seconds
2. WHEN open bets are queried THEN the system SHALL check Redis cache first before hitting PostgreSQL
3. WHEN cache misses occur THEN the system SHALL fall back to PostgreSQL transparently
4. WHEN Redis is unavailable THEN the system SHALL log a warning and operate directly from PostgreSQL

**Independent Test**: Query same market twice — second query should hit Redis, response time <10ms.

---

### P2: CSV Migration

**User Story**: As a bot operator, I want my existing paper trades migrated to PostgreSQL so that I don't lose historical data.

**Why P2**: Important for continuity but can be done as a one-time migration script.

**Acceptance Criteria**:

1. WHEN migration script runs THEN the system SHALL read all rows from `paper_trades.csv`
2. WHEN inserting migrated rows THEN the system SHALL set `trading_mode='paper'` and preserve all original fields
3. WHEN migration completes THEN the system SHALL output a count of migrated records
4. WHEN a migrated record conflicts with existing DB record (same market_id + timestamp) THEN the system SHALL skip it and log

**Independent Test**: Run migration, count CSV rows, count DB rows — they match (minus duplicates).

---

## Edge Cases

- WHEN PostgreSQL is unreachable at startup THEN the system SHALL exit with a clear error message
- WHEN Redis is unreachable THEN the system SHALL degrade to direct DB access with a warning log
- WHEN a bet with duplicate market_id and unresolved state exists THEN the system SHALL skip the new bet (maintain existing deduplication logic)
- WHEN CSV migration runs against empty CSV THEN the system SHALL complete successfully with 0 migrated records
- WHEN `TRADING_MODE=live` but no live trading infrastructure exists THEN the system SHALL still record the bet in DB but NOT attempt blockchain execution

---

## Success Criteria

- [ ] All new bets appear in PostgreSQL within 50ms of creation
- [ ] Redis cache hit rate >80% for repeated market lookups (when enabled)
- [ ] Existing CSV data fully migrated with zero loss
- [ ] Bot behavior in `paper` mode is identical to pre-migration state
- [ ] Switching `TRADING_MODE` env var changes bet tagging without code changes
