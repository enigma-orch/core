-- migrate:up
-- Transactional outbox for projecting social writes into the derived graph
-- store (Neo4j). Rows are inserted in the same transaction as the social
-- change; a worker drains unprocessed rows and applies them to Neo4j.
CREATE TABLE social_outbox (
    id           BIGSERIAL    PRIMARY KEY,
    occurred_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    event_type   TEXT         NOT NULL,
    payload      JSONB        NOT NULL,
    processed_at TIMESTAMPTZ,
    CONSTRAINT social_outbox_event_type_check
        CHECK (event_type IN (
            'follow.created',
            'follow.deleted',
            'outfit.shared',
            'outfit.share_revoked'
        ))
);

-- Partial index keeps the projector's claim query fast even after millions
-- of processed rows accumulate.
CREATE INDEX idx_social_outbox_unprocessed
    ON social_outbox (id)
    WHERE processed_at IS NULL;

-- migrate:down
DROP TABLE IF EXISTS social_outbox;
