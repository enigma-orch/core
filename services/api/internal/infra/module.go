package infra

import (
	"context"
	"log/slog"
	"os"

	"enigma/internal/config"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"go.uber.org/fx"
)

// Module wires the long-lived infrastructure singletons (logger, db pool,
// redis client) and registers their Stop hooks with Fx.
var Module = fx.Module("infra",
	fx.Provide(
		NewLogger,
		NewDatabasePool,
		NewRedisFromConfig,
	),
)

// NewLogger returns the process-wide structured logger. It is also installed
// as the slog default so packages that can't accept injection still get
// structured output.
func NewLogger() *slog.Logger {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	slog.SetDefault(logger)
	return logger
}

// NewDatabasePool builds the pgx pool and registers Close() on shutdown.
func NewDatabasePool(lc fx.Lifecycle, cfg *config.Config) (*pgxpool.Pool, error) {
	pool, err := NewPool(context.Background(), cfg.PostgresURL, cfg.DatabaseMaxConns, cfg.DatabaseMaxConnLife, cfg.DatabaseMaxConnIdle)
	if err != nil {
		return nil, err
	}
	lc.Append(fx.StopHook(func() { pool.Close() }))
	return pool, nil
}

// NewRedisFromConfig builds the Redis client and registers Close() on shutdown.
func NewRedisFromConfig(lc fx.Lifecycle, cfg *config.Config) *redis.Client {
	client := NewRedisClient(cfg.RedisURL)
	lc.Append(fx.StopHook(func() error { return client.Close() }))
	return client
}
