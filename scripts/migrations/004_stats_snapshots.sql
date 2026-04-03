-- Migration 004: Add system stats snapshots table
CREATE TABLE IF NOT EXISTS system_stats_snapshots (
    id          BIGSERIAL PRIMARY KEY,
    snapshot    JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stats_created ON system_stats_snapshots(created_at);