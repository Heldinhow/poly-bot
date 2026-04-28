# Polymarket Merge — Domain

## Core Business Rules

### 1. Underdog Selection
- Target markets where one outcome is priced ≤ 35% (`MAX_PRICE`)
- Maximum odds 20:1 (`MAX_ODDS`)
- Minimum 24h volume $10,000 (`MIN_VOLUME`)

### 2. Market Filtering (3 Stages)

```
Stage 1: Volume Filter
  └── Markets with volume_24h ≥ MIN_VOLUME

Stage 2: Live Market Filter
  └── Resolution within 48 hours
  └── Exclude: politics, future, financial

Stage 3: Value Filter
  └── Underdog price ≤ MAX_PRICE
  └── Odds ≤ MAX_ODDS
```

### 3. AI Analysis
- 3 agents run concurrently
- Each returns: `probability`, `confidence`, `reasoning`
- Average probability across successful agents
- If any agent fails, others continue

### 4. Edge Calculation
```
edge = (ai_probability * odds) - 1.0

Where:
  odds = 1.0 / underdog_price
```

### 5. Decision Rules

| Condition | Action |
|-----------|--------|
| `edge < MIN_EDGE` (default 5%) | REJECT |
| `ai_probability < implied_probability * 0.85` | REJECT |
| `edge >= 15%` | HIGH conviction |
| `edge >= 5%` | MEDIUM conviction |
| `edge < 5%` but `> min_edge` | LOW conviction |

### 6. Position Sizing (Kelly Criterion)
```
stake = kelly_frac * ((b * p - q) / b) * bankroll

Where:
  b = odds - 1
  p = ai_probability (or 1/odds if no AI)
  q = 1 - p
  kelly_frac = 0.25 (25%, conservative)
```

**Constraints:**
- Minimum stake: $1.00 (Polymarket minimum)
- Maximum stake: 10% of current bankroll

### 7. Deduplication
- Only one open bet per market_id per trading_mode
- Checked via `has_open_bet_for_market()` in repository

### 8. Resolution
- Poll closed markets via Polymarket API
- Winner = outcome with price closest to 1.0
- If winner == bet.outcome → `win`, else → `lose`
- Update DB record with result and `resolved_at`

## Entities

### Bet
```
market_id       string    Polymarket market identifier
question        string    Market description
outcome         string    Selected outcome name
price           float     Entry price (0-1)
stake           float     Amount wagered
payout          float     Potential payout
kelly_frac      float     Kelly fraction used (default 0.25)
edge            float     Calculated edge at entry
timestamp       datetime  Bet creation time (UTC)
probability_ai  float     AI estimated true probability
analysis_summary string   Concatenated AI reasoning
resolved        bool      Has market resolved?
result          string    'win' | 'lose' | null
resolved_at     datetime  Resolution timestamp
trading_mode    string    'paper' | 'live'
```

### Market (from Polymarket API)
```
id              string
question        string
volume_24h      float
liquidity       float
yes_price       float
no_price        float
outcomes        list[MarketOutcome]
closed          bool
url             string
```

## Domain Constraints

- Bankroll never goes below 0 (position sizing prevents it)
- Bets only placed on unresolved markets
- AI analysis is best-effort; failed agents are ignored
- Edge must be positive and above minimum threshold
- Underdog must not be "too unlikely" per AI (85% rule)
