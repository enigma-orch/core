-- migrate:up
UPDATE outfits
SET worn_at = created_at
WHERE worn_at IS NULL;

-- migrate:down
-- intentionally a no-op: we cannot distinguish backfilled rows from genuinely-null ones
