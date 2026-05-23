-- migrate:up
-- ivfflat needs `lists` tuning that scales with row count and gives lower
-- recall on small tables (which our per-user item sets are). HNSW gives
-- better recall out-of-the-box with no tuning knob, at the cost of more
-- build time and disk. For our scale that tradeoff is the right one.
DROP INDEX IF EXISTS idx_items_embedding;
DROP INDEX IF EXISTS idx_outfits_embedding;

CREATE INDEX idx_items_embedding
    ON items USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_outfits_embedding
    ON outfits USING hnsw (embedding vector_cosine_ops);

-- migrate:down
DROP INDEX IF EXISTS idx_items_embedding;
DROP INDEX IF EXISTS idx_outfits_embedding;

CREATE INDEX idx_items_embedding
    ON items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_outfits_embedding
    ON outfits USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
