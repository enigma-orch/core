-- migrate:up
-- The feed query joins outfit_shares by outfit_id then filters on visibility.
-- A partial index that already filters by visibility lets the planner skip
-- private/link_only rows during the join lookup.
CREATE INDEX IF NOT EXISTS idx_outfit_shares_outfit_visibility
    ON outfit_shares(outfit_id, visibility)
    WHERE visibility IN ('PUBLIC', 'FOLLOWERS');

-- migrate:down
DROP INDEX IF EXISTS idx_outfit_shares_outfit_visibility;
