package infra

import (
	"context"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
)

// NewRedisClient parses redisURL, dials, and verifies connectivity via PING.
// On unrecoverable failure it terminates the process — at startup that's the
// signal we want.
func NewRedisClient(redisURL string) *redis.Client {
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("failed to parse redis url: %v", err)
	}

	client := redis.NewClient(opt)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		log.Fatalf("redis ping failed: %v", err)
	}

	return client
}
