-- name: EnqueueOutboxEvent :exec
INSERT INTO social_outbox (event_type, payload)
VALUES ($1, $2);

-- name: ClaimOutboxBatch :many
-- Claims a batch of unprocessed outbox rows for the projector to process.
-- FOR UPDATE SKIP LOCKED lets multiple worker replicas run safely against the
-- same outbox: each replica gets a disjoint set of rows and never blocks on
-- another replica's batch.
SELECT id, occurred_at, event_type, payload
FROM social_outbox
WHERE processed_at IS NULL
ORDER BY id
LIMIT $1
FOR UPDATE SKIP LOCKED;

-- name: MarkOutboxProcessed :exec
UPDATE social_outbox
SET processed_at = now()
WHERE id = ANY($1::bigint[]);
