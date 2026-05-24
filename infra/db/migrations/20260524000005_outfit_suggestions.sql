-- migrate:up

CREATE TABLE outfit_suggestions (
    id                UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID             NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_ids          JSONB            NOT NULL,
    preview_image_url TEXT,
    season            TEXT             NOT NULL,
    occasion          TEXT,
    score             DOUBLE PRECISION NOT NULL,
    vibe              TEXT,
    mood              TEXT,
    background_color  TEXT             NOT NULL DEFAULT '#FAFAFA',
    suggested_song    TEXT,
    expires_at        TIMESTAMPTZ      NOT NULL,
    created_at        TIMESTAMPTZ      NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX idx_outfit_suggestions_user_expires
    ON outfit_suggestions (user_id, expires_at);

-- migrate:down
DROP TABLE IF EXISTS outfit_suggestions;
