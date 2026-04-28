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

-- ============================================================
-- Scan Settings (single-row runtime config)
-- ============================================================

CREATE TABLE IF NOT EXISTS scan_settings (
    id                  INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    enabled             BOOLEAN DEFAULT true,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default row if not exists
INSERT INTO scan_settings (id, enabled) VALUES (1, true)
    ON CONFLICT (id) DO NOTHING;

-- Trigger for scan_settings updated_at
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_scan_settings_updated_at') THEN
        CREATE TRIGGER trg_scan_settings_updated_at
            BEFORE UPDATE ON scan_settings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END$$;

-- ============================================================
-- Market Analysis Cache (avoid re-analyzing same markets)
-- ============================================================

CREATE TABLE IF NOT EXISTS market_analysis_cache (
    market_id           TEXT PRIMARY KEY,
    question            TEXT NOT NULL,
    yes_price_at_analysis DECIMAL(10, 4) NOT NULL,
    no_price_at_analysis  DECIMAL(10, 4) NOT NULL,
    probability         DECIMAL(5, 4),
    confidence          DECIMAL(5, 4),
    reasoning           TEXT,
    agent_name          TEXT,
    decision            TEXT,  -- ACCEPT | REJECT | SKIP
    analyzed_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cache_analyzed_at ON market_analysis_cache(analyzed_at);
CREATE INDEX IF NOT EXISTS idx_cache_decision ON market_analysis_cache(decision);

-- ============================================================
-- Migrations for existing tables
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'execution_logs' AND column_name = 'agent_name') THEN
        ALTER TABLE execution_logs ADD COLUMN agent_name TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'execution_logs' AND column_name = 'prompt_used') THEN
        ALTER TABLE execution_logs ADD COLUMN prompt_used TEXT;
    END IF;
END$$;

-- ============================================================
-- Agent Runtime Tables
-- ============================================================

CREATE TABLE IF NOT EXISTS agents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL UNIQUE,
    description         TEXT,
    runtime             TEXT NOT NULL,  -- CLI name: claude, opencode, hermes, codex, etc.
    model               TEXT,
    system_prompt       TEXT,
    max_concurrent_tasks INT DEFAULT 1,
    max_retries         INT DEFAULT 1,
    custom_args         TEXT[] DEFAULT '{}',
    custom_env          JSONB DEFAULT '{}',
    is_active           BOOLEAN DEFAULT true,
    is_archived         BOOLEAN DEFAULT false,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skills (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    description         TEXT,
    content             TEXT NOT NULL,
    is_active           BOOLEAN DEFAULT true,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_skills (
    agent_id            UUID REFERENCES agents(id) ON DELETE CASCADE,
    skill_id            UUID REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, skill_id)
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id             TEXT NOT NULL,
    market_id           TEXT NOT NULL,
    agent_id            UUID REFERENCES agents(id),
    agent_name          TEXT,  -- denormalized for fast access
    runtime             TEXT NOT NULL,
    model               TEXT,
    status              TEXT NOT NULL DEFAULT 'queued',  -- queued | claimed | running | completed | failed | cancelled
    queued_at           TIMESTAMPTZ DEFAULT NOW(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    duration_ms         INT,
    probability         DECIMAL(5,4),
    confidence          DECIMAL(5,4),
    reasoning           TEXT,
    sources             JSONB,
    raw_output          TEXT,
    prompt_used         TEXT,
    error_message       TEXT,
    failure_reason      TEXT,  -- timeout | agent_error | runtime_offline | parse_error
    input_tokens        BIGINT DEFAULT 0,
    output_tokens       BIGINT DEFAULT 0,
    cache_read_tokens   BIGINT DEFAULT 0,
    cache_write_tokens  BIGINT DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS execution_steps (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_log_id    UUID REFERENCES execution_logs(id) ON DELETE CASCADE,
    seq                 INT NOT NULL,
    step_type           TEXT NOT NULL,  -- text | thinking | tool_use | tool_result | error | status
    content             TEXT,
    tool_name           TEXT,
    tool_input          JSONB,
    tool_output         TEXT,
    tool_call_id        TEXT,
    duration_ms         INT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for runtime tables
CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_skills_active ON skills(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_execution_logs_market ON execution_logs(market_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_status ON execution_logs(status);
CREATE INDEX IF NOT EXISTS idx_execution_logs_agent ON execution_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_task ON execution_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_execution_steps_log ON execution_steps(execution_log_id, seq);

-- ============================================================
-- Execution Audit Trail
-- ============================================================

CREATE TABLE IF NOT EXISTS truth_claims (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_log_id    UUID REFERENCES execution_logs(id) ON DELETE CASCADE,
    claim_type         TEXT NOT NULL DEFAULT 'fact',
    content             TEXT NOT NULL,
    source_reference    TEXT,
    confidence_weight   DECIMAL(5,4),
    order_index         INT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_truth_claims_execution ON truth_claims(execution_log_id);

CREATE TABLE IF NOT EXISTS decision_factors (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_log_id        UUID REFERENCES execution_logs(id) ON DELETE CASCADE,
    market_id               TEXT NOT NULL,
    implied_probability     DECIMAL(5,4) NOT NULL,
    ai_probability          DECIMAL(5,4) NOT NULL,
    odds                    DECIMAL(10,4) NOT NULL,
    edge                    DECIMAL(10,4) NOT NULL,
    decision                TEXT NOT NULL,
    reject_reason           TEXT,
    bet_id                  INTEGER REFERENCES bets(id) ON DELETE SET NULL,
    stake                   DECIMAL(12,2),
    kelly_fraction          DECIMAL(5,2),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_decision_factors_market ON decision_factors(market_id);
CREATE INDEX IF NOT EXISTS idx_decision_factors_decision ON decision_factors(decision);
CREATE INDEX IF NOT EXISTS idx_decision_factors_bet ON decision_factors(bet_id);

CREATE TABLE IF NOT EXISTS execution_summary (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id               TEXT NOT NULL UNIQUE,
    question                TEXT,
    yes_price_at_analysis   DECIMAL(10,4),
    no_price_at_analysis    DECIMAL(10,4),
    volume_24h              DECIMAL(12,2),
    resolution_date         TEXT,
    agent_names             TEXT[],
    probabilities           DECIMAL(5,4)[],
    confidences             DECIMAL(5,4)[],
    reasoning_summary       TEXT,
    decision                TEXT,
    reject_reason           TEXT,
    edge                    DECIMAL(10,4),
    bet_id                  INTEGER REFERENCES bets(id) ON DELETE SET NULL,
    stake                   DECIMAL(12,2),
    outcome                 TEXT,
    bet_result              VARCHAR(10),
    first_execution_id      UUID REFERENCES execution_logs(id),
    last_execution_id       UUID REFERENCES execution_logs(id),
    execution_count         INT DEFAULT 0,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_execution_summary_decision ON execution_summary(decision);
CREATE INDEX IF NOT EXISTS idx_execution_summary_created ON execution_summary(created_at);
CREATE INDEX IF NOT EXISTS idx_execution_summary_bet_result ON execution_summary(bet_result);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'execution_logs' AND column_name = 'reject_reason') THEN
        ALTER TABLE execution_logs ADD COLUMN reject_reason TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'execution_logs' AND column_name = 'odds') THEN
        ALTER TABLE execution_logs ADD COLUMN odds DECIMAL(10,4);
    END IF;
END$$;

-- Trigger function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach triggers
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_agents_updated_at') THEN
        CREATE TRIGGER trg_agents_updated_at
            BEFORE UPDATE ON agents
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_skills_updated_at') THEN
        CREATE TRIGGER trg_skills_updated_at
            BEFORE UPDATE ON skills
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END$$;
