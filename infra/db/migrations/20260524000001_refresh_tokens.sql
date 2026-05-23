-- migrate:up
ALTER TABLE users
    ADD COLUMN refresh_token_hash TEXT,
    ADD COLUMN refresh_token_expires_at TIMESTAMPTZ;

CREATE INDEX idx_users_refresh_token_hash ON users(refresh_token_hash) WHERE refresh_token_hash IS NOT NULL;

-- migrate:down
DROP INDEX IF EXISTS idx_users_refresh_token_hash;
ALTER TABLE users
    DROP COLUMN IF EXISTS refresh_token_hash,
    DROP COLUMN IF EXISTS refresh_token_expires_at;
