-- migrate:up
CREATE TYPE visibility_enum AS ENUM ('PUBLIC', 'FOLLOWERS', 'LINK_ONLY', 'PRIVATE');

CREATE TABLE follows (
    follower_id UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followee_id UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, followee_id)
);
CREATE INDEX idx_follows_followee ON follows(followee_id);

CREATE TABLE outfit_shares (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    outfit_id   UUID            NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
    owner_id    UUID            NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    visibility  visibility_enum NOT NULL DEFAULT 'PUBLIC',
    share_token TEXT            UNIQUE,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT now()
);
CREATE INDEX idx_outfit_shares_owner   ON outfit_shares(owner_id);
CREATE INDEX idx_outfit_shares_outfit  ON outfit_shares(outfit_id);
CREATE INDEX idx_outfit_shares_token   ON outfit_shares(share_token) WHERE share_token IS NOT NULL;

-- migrate:down
DROP TABLE IF EXISTS outfit_shares;
DROP TABLE IF EXISTS follows;
DROP TYPE IF EXISTS visibility_enum;
