-- PostgreSQL schema for Polymarket Merge bot

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trading_mode') THEN
        CREATE TYPE trading_mode AS ENUM ('paper', 'live');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS bets (
    id              SERIAL PRIMARY KEY,
    market_id       VARCHAR(64) NOT NULL,
    question        TEXT NOT NULL,
    outcome         VARCHAR(255) NOT NULL,
    price           DECIMAL(10, 4) NOT NULL,
    stake           DECIMAL(12, 2) NOT NULL,
    payout          DECIMAL(12, 2) NOT NULL,
    kelly_frac      DECIMAL(5, 2) NOT NULL,
    edge            DECIMAL(10, 4) NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    probability_ai  DECIMAL(10, 4),
    analysis_summary TEXT,
    resolved        BOOLEAN DEFAULT FALSE,
    result          VARCHAR(10),
    resolved_at     TIMESTAMPTZ,
    trading_mode    trading_mode NOT NULL DEFAULT 'paper',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_bets_market_id ON bets(market_id);
CREATE INDEX IF NOT EXISTS idx_bets_trading_mode ON bets(trading_mode);
CREATE INDEX IF NOT EXISTS idx_bets_resolved ON bets(resolved);
CREATE INDEX IF NOT EXISTS idx_bets_timestamp ON bets(timestamp);
CREATE INDEX IF NOT EXISTS idx_bets_open ON bets(resolved, trading_mode) WHERE resolved = FALSE;

-- Unique constraint to prevent duplicate open bets per market + mode
CREATE UNIQUE INDEX IF NOT EXISTS idx_bets_unique_open
    ON bets(market_id, trading_mode)
    WHERE resolved = FALSE;
