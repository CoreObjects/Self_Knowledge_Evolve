-- Migration 005: Add relation_candidates table for unknown predicate discovery
CREATE TABLE IF NOT EXISTS governance.relation_candidates (
    id                  BIGSERIAL PRIMARY KEY,
    candidate_id        UUID         NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    predicate_name      VARCHAR(128) NOT NULL,
    normalized_name     VARCHAR(128),
    examples            JSONB        DEFAULT '[]',
    source_count        INTEGER      NOT NULL DEFAULT 1,
    source_diversity    NUMERIC(4,3) DEFAULT 0.0,
    review_status       VARCHAR(32)  NOT NULL DEFAULT 'discovered',
    reviewer            VARCHAR(128),
    review_note         TEXT,
    first_seen_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (normalized_name)
);