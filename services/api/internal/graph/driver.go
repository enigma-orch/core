package graph

import (
	"context"
	"fmt"
	"time"

	"enigma/internal/config"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

// NewDriver builds a Neo4j driver from config and verifies connectivity. The
// caller (Fx module) owns the lifecycle and is responsible for calling Close
// on shutdown.
func NewDriver(cfg *config.Config) (neo4j.DriverWithContext, error) {
	if cfg.Neo4jURL == "" {
		return nil, fmt.Errorf("NEO4J_URL is required when GRAPH_ENABLED=true")
	}
	driver, err := neo4j.NewDriverWithContext(
		cfg.Neo4jURL,
		neo4j.BasicAuth(cfg.Neo4jUser, cfg.Neo4jPassword, ""),
	)
	if err != nil {
		return nil, fmt.Errorf("creating neo4j driver: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := driver.VerifyConnectivity(ctx); err != nil {
		_ = driver.Close(context.Background())
		return nil, fmt.Errorf("verifying neo4j connectivity: %w", err)
	}
	return driver, nil
}
