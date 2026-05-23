-- migrate:up
CREATE TABLE outfit_likes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    outfit_id   UUID        NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_outfit_likes_user_outfit UNIQUE (user_id, outfit_id)
);
CREATE INDEX idx_outfit_likes_outfit ON outfit_likes(outfit_id);
CREATE INDEX idx_outfit_likes_user   ON outfit_likes(user_id);

-- migrate:down
DROP TABLE IF EXISTS outfit_likes;
