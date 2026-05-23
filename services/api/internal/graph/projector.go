package graph

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"time"

	"enigma/internal/repository"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

// Projector drains social_outbox rows from Postgres and applies them as
// Cypher writes against the derived Neo4j store. Multiple replicas may run
// concurrently — the SKIP LOCKED claim in ClaimOutboxBatch keeps batches
// disjoint.
type Projector struct {
	repo         repository.SocialRepository
	driver       neo4j.DriverWithContext
	log          *slog.Logger
	pollInterval time.Duration
	batchSize    int32
}

func NewProjector(
	repo repository.SocialRepository,
	driver neo4j.DriverWithContext,
	log *slog.Logger,
	pollInterval time.Duration,
	batchSize int,
) *Projector {
	if batchSize <= 0 {
		batchSize = 100
	}
	if pollInterval <= 0 {
		pollInterval = 2 * time.Second
	}
	return &Projector{
		repo:         repo,
		driver:       driver,
		log:          log.With("component", "graph.projector"),
		pollInterval: pollInterval,
		batchSize:    int32(batchSize),
	}
}

// Run blocks until ctx is cancelled, processing batches in a loop. Errors
// during one batch are logged but do not stop the loop; the rows remain
// unprocessed and will be retried on the next tick.
func (p *Projector) Run(ctx context.Context) {
	p.log.InfoContext(ctx, "projector started", "batch_size", p.batchSize, "interval", p.pollInterval)
	ticker := time.NewTicker(p.pollInterval)
	defer ticker.Stop()

	for {
		// Drain whatever is waiting, then wait for the next tick.
		processed, err := p.drainOnce(ctx)
		if err != nil && !errors.Is(err, context.Canceled) {
			p.log.ErrorContext(ctx, "projector batch failed", "error", err)
		}
		if processed == 0 {
			select {
			case <-ctx.Done():
				p.log.InfoContext(ctx, "projector stopping")
				return
			case <-ticker.C:
			}
			continue
		}
		// More likely waiting in the outbox — keep draining without sleeping.
		select {
		case <-ctx.Done():
			p.log.InfoContext(ctx, "projector stopping")
			return
		default:
		}
	}
}

// drainOnce claims one batch, applies it to Neo4j, and marks the rows
// processed. Returns the number of rows applied (so the caller knows whether
// to keep draining or sleep).
func (p *Projector) drainOnce(ctx context.Context) (int, error) {
	var processed int
	err := p.repo.WithTx(ctx, func(txRepo repository.SocialRepository) error {
		rows, err := txRepo.ClaimOutboxBatch(ctx, p.batchSize)
		if err != nil {
			return fmt.Errorf("claiming outbox batch: %w", err)
		}
		if len(rows) == 0 {
			return nil
		}

		if err := p.applyBatch(ctx, rows); err != nil {
			return fmt.Errorf("applying batch: %w", err)
		}

		ids := make([]int64, len(rows))
		for i, r := range rows {
			ids[i] = r.ID
		}
		if err := txRepo.MarkOutboxProcessed(ctx, ids); err != nil {
			return fmt.Errorf("marking outbox processed: %w", err)
		}
		processed = len(rows)
		return nil
	})
	return processed, err
}

// applyBatch writes the events to Neo4j inside a single session/transaction so
// the projection is consistent per batch.
func (p *Projector) applyBatch(ctx context.Context, rows []repository.ClaimOutboxBatchRow) error {
	session := p.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		for _, row := range rows {
			if err := applyEvent(ctx, tx, row); err != nil {
				return nil, err
			}
		}
		return nil, nil
	})
	return err
}

// applyEvent dispatches a single outbox row to the matching Cypher write.
// Unknown event types are logged and skipped (so a stuck row never blocks the
// queue if a producer ships an event the projector doesn't understand yet).
func applyEvent(ctx context.Context, tx neo4j.ManagedTransaction, row repository.ClaimOutboxBatchRow) error {
	switch row.EventType {
	case repository.EventFollowCreated:
		var p repository.FollowEventPayload
		if err := json.Unmarshal(row.Payload, &p); err != nil {
			return fmt.Errorf("decoding %s payload: %w", row.EventType, err)
		}
		_, err := tx.Run(ctx, `
			MERGE (follower:User {id: $follower_id})
			MERGE (followee:User {id: $followee_id})
			MERGE (follower)-[r:FOLLOWS]->(followee)
			ON CREATE SET r.since = datetime($since)
		`, map[string]any{
			"follower_id": p.FollowerID.String(),
			"followee_id": p.FolloweeID.String(),
			"since":       row.OccurredAt.Time.Format(time.RFC3339),
		})
		return err

	case repository.EventFollowDeleted:
		var p repository.FollowEventPayload
		if err := json.Unmarshal(row.Payload, &p); err != nil {
			return fmt.Errorf("decoding %s payload: %w", row.EventType, err)
		}
		_, err := tx.Run(ctx, `
			MATCH (follower:User {id: $follower_id})-[r:FOLLOWS]->(followee:User {id: $followee_id})
			DELETE r
		`, map[string]any{
			"follower_id": p.FollowerID.String(),
			"followee_id": p.FolloweeID.String(),
		})
		return err

	case repository.EventOutfitShared:
		var p repository.OutfitSharedPayload
		if err := json.Unmarshal(row.Payload, &p); err != nil {
			return fmt.Errorf("decoding %s payload: %w", row.EventType, err)
		}
		_, err := tx.Run(ctx, `
			MERGE (owner:User {id: $owner_id})
			MERGE (outfit:Outfit {id: $outfit_id})
			SET outfit.visibility = $visibility
			MERGE (owner)-[:OWNS]->(outfit)
		`, map[string]any{
			"owner_id":   p.OwnerID.String(),
			"outfit_id":  p.OutfitID.String(),
			"visibility": p.Visibility,
		})
		return err

	case repository.EventOutfitShareRevoked:
		var p repository.OutfitSharedPayload
		if err := json.Unmarshal(row.Payload, &p); err != nil {
			return fmt.Errorf("decoding %s payload: %w", row.EventType, err)
		}
		_, err := tx.Run(ctx, `
			MATCH (outfit:Outfit {id: $outfit_id})
			SET outfit.visibility = 'private'
		`, map[string]any{
			"outfit_id": p.OutfitID.String(),
		})
		return err

	default:
		// Don't fail the batch on an unknown type — log and accept it as
		// processed so the queue keeps moving.
		return nil
	}
}
