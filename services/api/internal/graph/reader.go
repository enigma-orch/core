package graph

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

// Reader exposes the read-only graph queries served by the
// /api/v1/graph/* endpoints. Implementations talk to Neo4j; the interface
// keeps the HTTP handlers testable with a fake.
type Reader interface {
	SuggestedFollows(ctx context.Context, viewerID uuid.UUID, limit int) ([]SuggestedFollow, error)
	MutualFollowers(ctx context.Context, viewerID, otherID uuid.UUID, limit int) ([]uuid.UUID, error)
	TasteSimilarUsers(ctx context.Context, viewerID uuid.UUID, limit int) ([]TasteSimilarUser, error)
}

type SuggestedFollow struct {
	UserID   uuid.UUID `json:"user_id"`
	Strength int64     `json:"strength"`
}

type TasteSimilarUser struct {
	UserID  uuid.UUID `json:"user_id"`
	Overlap int64     `json:"overlap"`
}

type cypherReader struct {
	driver neo4j.DriverWithContext
}

func NewReader(driver neo4j.DriverWithContext) Reader {
	return &cypherReader{driver: driver}
}

func clampLimit(limit, fallback, max int) int {
	if limit <= 0 {
		return fallback
	}
	if limit > max {
		return max
	}
	return limit
}

func (r *cypherReader) SuggestedFollows(ctx context.Context, viewerID uuid.UUID, limit int) ([]SuggestedFollow, error) {
	limit = clampLimit(limit, 20, 100)
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	res, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		rows, err := tx.Run(ctx, `
			MATCH (me:User {id: $me})-[:FOLLOWS]->(:User)-[:FOLLOWS]->(c:User)
			WHERE NOT (me)-[:FOLLOWS]->(c) AND c.id <> $me
			RETURN c.id AS user_id, count(*) AS strength
			ORDER BY strength DESC
			LIMIT $limit
		`, map[string]any{
			"me":    viewerID.String(),
			"limit": limit,
		})
		if err != nil {
			return nil, err
		}
		var out []SuggestedFollow
		for rows.Next(ctx) {
			rec := rows.Record()
			idStr, _ := rec.Get("user_id")
			strength, _ := rec.Get("strength")
			id, err := uuid.Parse(idStr.(string))
			if err != nil {
				return nil, fmt.Errorf("parsing user_id from suggested-follows: %w", err)
			}
			out = append(out, SuggestedFollow{UserID: id, Strength: strength.(int64)})
		}
		return out, rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return res.([]SuggestedFollow), nil
}

func (r *cypherReader) MutualFollowers(ctx context.Context, viewerID, otherID uuid.UUID, limit int) ([]uuid.UUID, error) {
	limit = clampLimit(limit, 50, 200)
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	res, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		rows, err := tx.Run(ctx, `
			MATCH (me:User {id: $me})-[:FOLLOWS]->(m:User)<-[:FOLLOWS]-(:User {id: $other})
			RETURN m.id AS user_id
			LIMIT $limit
		`, map[string]any{
			"me":    viewerID.String(),
			"other": otherID.String(),
			"limit": limit,
		})
		if err != nil {
			return nil, err
		}
		var out []uuid.UUID
		for rows.Next(ctx) {
			idStr, _ := rows.Record().Get("user_id")
			id, err := uuid.Parse(idStr.(string))
			if err != nil {
				return nil, fmt.Errorf("parsing user_id from mutual-followers: %w", err)
			}
			out = append(out, id)
		}
		return out, rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return res.([]uuid.UUID), nil
}

func (r *cypherReader) TasteSimilarUsers(ctx context.Context, viewerID uuid.UUID, limit int) ([]TasteSimilarUser, error) {
	limit = clampLimit(limit, 20, 100)
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	res, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		rows, err := tx.Run(ctx, `
			MATCH (me:User {id: $me})-[:LIKED]->(o:Outfit)<-[:LIKED]-(other:User)
			WHERE other.id <> $me
			RETURN other.id AS user_id, count(o) AS overlap
			ORDER BY overlap DESC
			LIMIT $limit
		`, map[string]any{
			"me":    viewerID.String(),
			"limit": limit,
		})
		if err != nil {
			return nil, err
		}
		var out []TasteSimilarUser
		for rows.Next(ctx) {
			rec := rows.Record()
			idStr, _ := rec.Get("user_id")
			overlap, _ := rec.Get("overlap")
			id, err := uuid.Parse(idStr.(string))
			if err != nil {
				return nil, fmt.Errorf("parsing user_id from taste-similar: %w", err)
			}
			out = append(out, TasteSimilarUser{UserID: id, Overlap: overlap.(int64)})
		}
		return out, rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return res.([]TasteSimilarUser), nil
}
