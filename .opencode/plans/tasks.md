# Persistence & Trading Mode Tasks

**Design**: `.opencode/plans/design.md`  
**Status**: Draft

---

## Execution Plan

### Phase 1: Foundation (Sequential)

Setup infrastructure, dependencies, and configuration.

```
T1 → T2 → T3
```

### Phase 2: Core Implementation (Parallel OK)

After foundation, these can run in parallel.

```
      ┌→ T4 ─┐
T3 ──┼→ T5 ─┼──→ T8
      └→ T6 ─┘
T7 ───────────→
```

### Phase 3: Integration & Migration (Sequential)

Wire everything together and migrate data.

```
T8 → T9 → T10
```

---

## Task Breakdown

### T1: Add dependencies to requirements.txt

**What**: Add `psycopg2-binary`, `redis` to requirements.txt
**Where**: `requirements.txt`
**Depends on**: None
**Reuses**: None

**Done when**:

- [ ] `psycopg2-binary>=2.9.0` added
- [ ] `redis>=5.0.0` added
- [ ] `pip install -r requirements.txt` completes without errors

**Verify**:
```bash
pip install -r requirements.txt
python -c "import psycopg2; import redis; print('OK')"
```

---

### T2: Extend Settings with DB/Redis/TradingMode config

**What**: Add `database_url`, `redis_url`, `trading_mode`, `redis_ttl_seconds` to Pydantic Settings
**Where**: `config.py`
**Depends on**: None
**Reuses**: Existing `Settings` class pattern

**Done when**:

- [ ] `database_url: str` field added (required)
- [ ] `redis_url: Optional[str] = None` field added
- [ ] `trading_mode: str = "paper"` field added with validator (`paper` or `live`)
- [ ] `redis_ttl_seconds: int = 60` field added
- [ ] Invalid `trading_mode` defaults to `paper` with warning log
- [ ] Existing `paper_mode` bool marked as deprecated (keep for backwards compat)

**Verify**:
```bash
python -c "from config import get_settings; s=get_settings(); print(s.trading_mode, s.database_url)"
```

---

### T3: Create PostgreSQL schema and connection module

**What**: SQL schema definition and database connection manager
**Where**: `db/schema.sql`, `db/connection.py`
**Depends on**: T2
**Reuses**: None

**Done when**:

- [ ] `db/schema.sql` created with `bets` table, indexes, and `trading_mode` enum
- [ ] `db/connection.py` created with `get_db_connection()` function using `psycopg2`
- [ ] Connection pooling configured (min 1, max 5)
- [ ] Connection string parsed from `DATABASE_URL`
- [ ] Basic health check query works: `SELECT 1`

**Verify**:
```bash
# Requires local PostgreSQL running
python -c "from db.connection import get_db_connection; conn=get_db_connection(); cur=conn.cursor(); cur.execute('SELECT 1'); print(cur.fetchone())"
```

---

### T4: Create BetRepository class [P]

**What**: Repository pattern for bet CRUD operations
**Where**: `db/repository.py`
**Depends on**: T3
**Reuses**: `PaperBet` field semantics

**Done when**:

- [ ] `BetRepository` class created
- [ ] `create_bet(bet: Bet) -> int` — returns inserted bet ID
- [ ] `get_open_bets(trading_mode: Optional[str]) -> list[Bet]`
- [ ] `get_bet_by_market_id(market_id: str) -> Optional[Bet]`
- [ ] `resolve_bet(market_id: str, won: bool) -> bool`
- [ ] `get_bet_history()` with optional filters
- [ ] All methods use parameterized queries (SQL injection safe)

**Verify**:
```bash
python -c "from db.repository import BetRepository; r=BetRepository(); print('OK')"
```

---

### T5: Create Bet dataclass with trading_mode [P]

**What**: Replace/extend `PaperBet` to include `trading_mode` and DB fields
**Where**: `models/bet.py` (new file)
**Depends on**: None
**Reuses**: `PaperBet` from `portfolio.py`

**Done when**:

- [ ] `Bet` dataclass created with all fields from design
- [ ] `trading_mode: str` field included, default `"paper"`
- [ ] `to_row()` and `from_row()` methods for DB serialization
- [ ] Backwards compatibility: `PaperBet` can convert to/from `Bet`
- [ ] `portfolio.py` updated to import `Bet` instead of local `PaperBet`

**Verify**:
```bash
python -c "from models.bet import Bet; b=Bet(market_id='123', question='Test', outcome='Yes', price=0.5, stake=1, payout=2, kelly_frac=0.25, edge=0.1, timestamp='2024-01-01', trading_mode='paper'); print(b)"
```

---

### T6: Create Redis MarketCache [P]

**What**: Cache wrapper for market data and bet state
**Where**: `cache/market_cache.py`
**Depends on**: T2
**Reuses**: None

**Done when**:

- [ ] `MarketCache` class created
- [ ] `get_market(market_id: str)` — returns deserialized Market or None
- [ ] `set_market(market_id: str, data, ttl)` — serializes and stores
- [ ] `get_open_bets(mode)` — cached list of open bet IDs
- [ ] `set_open_bets(mode, bets)` — cache with TTL
- [ ] Graceful degradation when Redis is unavailable (log warning, return None)

**Verify**:
```bash
# Requires local Redis running
python -c "from cache.market_cache import MarketCache; c=MarketCache(); c.set_market('123', {'question':'Test'}); print(c.get_market('123'))"
```

---

### T7: Create TradingModeGate [P]

**What**: Trading mode enforcement and validation
**Where**: `trading/mode_gate.py`
**Depends on**: T2
**Reuses**: Existing `get_settings()`

**Done when**:

- [ ] `TradingModeGate` class created
- [ ] `get_current_mode() -> str` reads from settings
- [ ] `is_live_enabled() -> bool`
- [ ] `validate_bet_allowed() -> bool` — always True for now, but enforces mode check
- [ ] `get_mode_for_bet() -> str` — returns current mode string for tagging
- [ ] Logs mode prominently at startup

**Verify**:
```bash
python -c "from trading.mode_gate import TradingModeGate; g=TradingModeGate(); print(g.get_current_mode(), g.is_live_enabled())"
```

---

### T8: Refactor PaperPortfolio to use BetRepository

**What**: Replace CSV persistence with PostgreSQL via Repository
**Where**: `portfolio.py` (modify)
**Depends on**: T4, T5, T7
**Reuses**: Existing `PaperPortfolio` logic, `BetRepository`

**Done when**:

- [ ] `PaperPortfolio` accepts `BetRepository` in constructor
- [ ] `_load_csv()` replaced with `repository.get_open_bets()`
- [ ] `_save_csv()` replaced with `repository.create_bet()` / `repository.resolve_bet()`
- [ ] CSV file no longer written to (read-only for migration)
- [ ] `record_bet()` tags bet with `trading_mode` from `TradingModeGate`
- [ ] `stats()` still works, reading from repository

**Verify**:
```bash
python -c "from portfolio import PaperPortfolio; from db.repository import BetRepository; p=PaperPortfolio(repo=BetRepository()); print(p.stats())"
```

---

### T9: Create CSV migration script

**What**: One-time script to migrate existing CSV data to PostgreSQL
**Where**: `scripts/migrate_csv.py`
**Depends on**: T4, T5
**Reuses**: CSV parsing from old `PaperPortfolio._load_csv()`

**Done when**:

- [ ] Script reads `paper_trades.csv`
- [ ] Each row converted to `Bet` with `trading_mode='paper'`
- [ ] Inserts via `BetRepository.create_bet()`
- [ ] Duplicates skipped (same market_id + timestamp)
- [ ] Outputs migration summary: total, migrated, skipped
- [ ] Idempotent — running twice doesn't duplicate

**Verify**:
```bash
python scripts/migrate_csv.py
# Check DB: SELECT COUNT(*) FROM bets WHERE trading_mode='paper'; should match CSV row count
```

---

### T10: Wire everything in main.py and test end-to-end

**What**: Update main entry point to initialize DB, Redis, and new components
**Where**: `main.py` (modify)
**Depends on**: T8, T9
**Reuses**: Existing main loop structure

**Done when**:

- [ ] `main.py` creates `BetRepository` and passes to `PaperPortfolio`
- [ ] `main.py` creates `MarketCache` (if Redis configured)
- [ ] `main.py` creates `TradingModeGate` and logs mode at startup
- [ ] `main.py` handles DB connection errors gracefully (exit with error)
- [ ] Bot runs one full cycle successfully in paper mode
- [ ] New bet appears in PostgreSQL after cycle

**Verify**:
```bash
# Start bot, let it run one cycle, check DB
python main.py
# In another terminal: psql -c "SELECT * FROM bets ORDER BY id DESC LIMIT 1;"
```

---

## Parallel Execution Map

```
Phase 1 (Sequential):
  T1 ──→ T2 ──→ T3

Phase 2 (Parallel):
  T3 complete, then:
    ├── T4 [P] ──→┐
    ├── T5 [P] ──→┼──→ T8
    ├── T6 [P] ──→┘
    └── T7 [P] ─────────────────→

Phase 3 (Sequential):
  T4, T5, T6, T7, T8 complete, then:
    T9 ──→ T10
```

---

## Task Granularity Check

| Task | Scope | Status |
|------|-------|--------|
| T1: Add dependencies | 1 file | ✅ Granular |
| T2: Extend Settings | 1 class | ✅ Granular |
| T3: DB schema + connection | 2 files, 1 concept | ✅ Granular |
| T4: BetRepository | 1 class | ✅ Granular |
| T5: Bet dataclass | 1 dataclass | ✅ Granular |
| T6: MarketCache | 1 class | ✅ Granular |
| T7: TradingModeGate | 1 class | ✅ Granular |
| T8: Refactor Portfolio | 1 file refactor | ✅ Granular |
| T9: Migration script | 1 script | ✅ Granular |
| T10: Wire main.py | 1 file integration | ✅ Granular |

---

## Priority by Impact

| Task | Impact | Confiança | Esforço | Score | Priority |
|------|--------|-----------|---------|-------|----------|
| T1-T3 (Foundation) | Alto | Alta | Médio | 6 | 🔴 Must do first |
| T4 (Repository) | Alto | Alta | Médio | 6 | 🔴 Must do first |
| T5 (Bet model) | Alto | Alta | Baixo | 9 | 🔴 Must do first |
| T8 (Portfolio refactor) | Alto | Alta | Médio | 6 | 🔴 Must do first |
| T7 (Mode gate) | Médio | Alta | Baixo | 6 | 🟡 Should do |
| T9 (Migration) | Médio | Alta | Baixo | 6 | 🟡 Should do |
| T10 (Integration) | Alto | Alta | Médio | 6 | 🔴 Must do |
| T6 (Redis cache) | Médio | Média | Médio | 3 | 🟢 Nice to have |

**Note**: T6 (Redis) can be deferred to a follow-up if needed. PostgreSQL alone satisfies the MVP.
