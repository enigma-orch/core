-- migrate:up
ALTER TABLE scraped_outfits
    ADD COLUMN source_type TEXT NOT NULL DEFAULT 'social';

CREATE INDEX idx_scraped_outfits_user_retail
    ON scraped_outfits(user_id, created_at DESC)
    WHERE source_type = 'retail';

CREATE TABLE daily_outfit_picks (
    user_id          UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pick_date        DATE         NOT NULL,
    outfit_id        UUID         NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
    spotify_context  JSONB,
    weather_snapshot JSONB,
    reason           TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, pick_date)
);
CREATE INDEX idx_daily_outfit_picks_outfit ON daily_outfit_picks(outfit_id);

-- migrate:down
DROP INDEX IF EXISTS idx_daily_outfit_picks_outfit;
DROP TABLE IF EXISTS daily_outfit_picks;
DROP INDEX IF EXISTS idx_scraped_outfits_user_retail;
ALTER TABLE scraped_outfits DROP COLUMN IF EXISTS source_type;
