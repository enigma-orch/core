-- migrate:up
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE mood_enum AS ENUM (
    'HAPPY', 'SAD', 'ENERGETIC', 'CALM', 'MELANCHOLIC',
    'ANGRY', 'RELAXED', 'FOCUSED', 'UNKNOWN'
);

CREATE TABLE users (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email                   VARCHAR(255) UNIQUE,
    display_name            VARCHAR(255),
    avatar_url              TEXT,
    mood                    mood_enum   NOT NULL DEFAULT 'UNKNOWN',
    location                VARCHAR(255),
    style_identity          VARCHAR(255),
    preferred_styles        TEXT[],
    preferred_colors        TEXT[],
    preferred_stores        TEXT[],
    budget_min              INTEGER,
    budget_max              INTEGER,
    tops_size               VARCHAR(50),
    bottoms_size            VARCHAR(50),
    shoes_size              VARCHAR(50),
    outerwear_size          VARCHAR(50),
    spotify_id              VARCHAR(255) UNIQUE,
    spotify_access_token    TEXT,
    spotify_refresh_token   TEXT,
    spotify_token_expires_at TIMESTAMPTZ,
    google_id               VARCHAR(255) UNIQUE,
    google_access_token     TEXT,
    google_refresh_token    TEXT,
    google_token_expires_at TIMESTAMPTZ,
    google_calendar_id      VARCHAR(255),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE clothing_items (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    category    VARCHAR(50)  NOT NULL,
    colors      JSON        NOT NULL DEFAULT '[]',
    brand       VARCHAR(255),
    style_tags  JSON        NOT NULL DEFAULT '[]',
    image_url   TEXT,
    is_favorite BOOLEAN     NOT NULL DEFAULT false,
    times_worn  INTEGER     NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_clothing_items_user_id ON clothing_items(user_id);

CREATE TABLE items (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_image_url  TEXT,
    clean_image_url     TEXT,
    name                TEXT,
    category            TEXT,
    subcategory         TEXT,
    brand               TEXT,
    colors              TEXT[],
    season              TEXT[],
    occasion            TEXT,
    style_tags          TEXT[],
    pattern             TEXT,
    vibe                TEXT,
    mood                TEXT,
    size                TEXT,
    notes               TEXT,
    wear_count          INTEGER     NOT NULL DEFAULT 0,
    last_worn_at        TIMESTAMPTZ,
    enriched            BOOLEAN     NOT NULL DEFAULT false,
    enrichment_data     JSONB,
    embedding           vector(768),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_items_user_id    ON items(user_id);
CREATE INDEX idx_items_category   ON items(user_id, category);
CREATE INDEX idx_items_last_worn  ON items(user_id, last_worn_at);
CREATE INDEX idx_items_embedding  ON items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE outfits (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                TEXT,
    preview_image_url   TEXT,
    occasion            TEXT,
    season              TEXT,
    vibe                TEXT,
    mood                TEXT,
    weather_context     TEXT,
    spotify_context     JSONB,
    source              TEXT        NOT NULL DEFAULT 'ai',
    rating              INTEGER,
    worn_at             TIMESTAMPTZ,
    wear_count          INTEGER     NOT NULL DEFAULT 0,
    embedding           vector(768),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_outfits_user_id  ON outfits(user_id);
CREATE INDEX idx_outfits_source   ON outfits(user_id, source);
CREATE INDEX idx_outfits_worn_at  ON outfits(user_id, worn_at);
CREATE INDEX idx_outfits_embedding ON outfits USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE outfit_items (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    outfit_id   UUID    NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
    item_id     UUID    NOT NULL REFERENCES items(id)   ON DELETE CASCADE,
    role        TEXT,
    position    INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_outfit_items_outfit_item UNIQUE (outfit_id, item_id)
);
CREATE INDEX idx_outfit_items_outfit ON outfit_items(outfit_id);
CREATE INDEX idx_outfit_items_item   ON outfit_items(item_id);

CREATE TABLE scraped_outfits (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_url       TEXT        NOT NULL,
    title           VARCHAR(500) NOT NULL,
    brand           VARCHAR(255),
    price           FLOAT,
    source_url      TEXT        NOT NULL,
    source_domain   VARCHAR(255),
    category        VARCHAR(100),
    tags            TEXT[],
    meta_data       JSONB,
    is_liked        BOOLEAN,
    seen_at         TIMESTAMPTZ,
    style_tags      TEXT[],
    weather_tags    TEXT[],
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_scraped_outfits_user_id ON scraped_outfits(user_id);

CREATE TABLE spotify_tracks (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    spotify_track_id VARCHAR(255) NOT NULL,
    track_name      VARCHAR(500) NOT NULL,
    artist_name     VARCHAR(500) NOT NULL,
    album_name      VARCHAR(500),
    album_image_url VARCHAR(1000),
    played_at       TIMESTAMPTZ NOT NULL,
    valence         FLOAT,
    energy          FLOAT,
    danceability    FLOAT,
    tempo           FLOAT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_spotify_tracks_user_id   ON spotify_tracks(user_id);
CREATE INDEX ix_spotify_tracks_played_at ON spotify_tracks(played_at);

-- migrate:down
DROP TABLE IF EXISTS spotify_tracks;
DROP TABLE IF EXISTS scraped_outfits;
DROP TABLE IF EXISTS outfit_items;
DROP TABLE IF EXISTS outfits;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS clothing_items;
DROP TABLE IF EXISTS users;
DROP TYPE IF EXISTS mood_enum;
