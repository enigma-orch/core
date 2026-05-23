-- migrate:up
CREATE TABLE galleries (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT        NOT NULL,
    description     TEXT,
    cover_image_url TEXT,
    is_public       BOOLEAN     NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_galleries_user_id ON galleries(user_id);
CREATE INDEX idx_galleries_public  ON galleries(is_public);

CREATE TABLE gallery_outfits (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    gallery_id  UUID    NOT NULL REFERENCES galleries(id) ON DELETE CASCADE,
    outfit_id   UUID    NOT NULL REFERENCES outfits(id)   ON DELETE CASCADE,
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_gallery_outfit UNIQUE (gallery_id, outfit_id)
);
CREATE INDEX idx_gallery_outfits_gallery ON gallery_outfits(gallery_id);
CREATE INDEX idx_gallery_outfits_outfit  ON gallery_outfits(outfit_id);

-- migrate:down
DROP TABLE IF EXISTS gallery_outfits;
DROP TABLE IF EXISTS galleries;
