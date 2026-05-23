package graph

import (
	"context"
	"log/slog"

	"enigma/internal/config"
	"enigma/internal/repository"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
	"go.uber.org/fx"
)

// Module wires the Neo4j-backed graph subsystem. When cfg.GraphEnabled is
// false the providers return nil-equivalents (graph endpoints will surface a
// clear error via the HTTP layer) and no projector goroutine is started.
var Module = fx.Module("graph",
	fx.Provide(
		newDriver,
		newReader,
		newProjector,
	),
	fx.Invoke(runProjector),
)

// newDriver returns nil when the graph subsystem is disabled. Callers must
// nil-check before use; the HTTP layer translates a nil reader into a 503.
func newDriver(lc fx.Lifecycle, cfg *config.Config) (neo4j.DriverWithContext, error) {
	if !cfg.GraphEnabled {
		return nil, nil
	}
	driver, err := NewDriver(cfg)
	if err != nil {
		return nil, err
	}
	lc.Append(fx.Hook{
		OnStop: func(ctx context.Context) error {
			return driver.Close(ctx)
		},
	})
	return driver, nil
}

func newReader(driver neo4j.DriverWithContext) Reader {
	if driver == nil {
		return nil
	}
	return NewReader(driver)
}

func newProjector(
	cfg *config.Config,
	repo repository.SocialRepository,
	driver neo4j.DriverWithContext,
	log *slog.Logger,
) *Projector {
	if !cfg.GraphEnabled || driver == nil {
		return nil
	}
	return NewProjector(repo, driver, log, cfg.GraphPollInterval, cfg.GraphBatchSize)
}

func runProjector(lc fx.Lifecycle, log *slog.Logger, p *Projector) {
	if p == nil {
		log.Info("graph projector disabled (GRAPH_ENABLED=false)")
		return
	}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	lc.Append(fx.Hook{
		OnStart: func(_ context.Context) error {
			go func() {
				defer close(done)
				p.Run(ctx)
			}()
			return nil
		},
		OnStop: func(stopCtx context.Context) error {
			cancel()
			select {
			case <-done:
			case <-stopCtx.Done():
			}
			return nil
		},
	})
}
