package config

import (
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/joho/godotenv"
)

type Config struct {
	PostgresURL         string
	DatabaseURL         string
	DatabaseMaxConns    int32
	DatabaseMaxConnLife time.Duration
	DatabaseMaxConnIdle time.Duration

	RedisURL string

	ServerPort string
	ServerHost string

	Environment      string
	InternalAPIToken string

	SpotifyClientID     string
	SpotifyClientSecret string
	SpotifyRedirectURI  string
	JWTSecret           string
	CORSOrigins         string
	Argon2Salt          string

	// Graph (Neo4j) — optional derived store for social graph queries.
	// GraphEnabled gates the projector worker and the /api/v1/graph/* endpoints.
	GraphEnabled       bool
	Neo4jURL           string
	Neo4jUser          string
	Neo4jPassword      string
	GraphPollInterval  time.Duration
	GraphBatchSize     int
}

type Configuration = Config

func LoadConfig() (*Config, error) {
	_ = godotenv.Load()

	cfg := &Config{
		PostgresURL:         firstEnv("POSTGRES_URL", "POSTGRES_DB"),
		DatabaseURL:         firstEnv("DATABASE_URL", "POSTGRES_URL", "POSTGRES_DB"),
		DatabaseMaxConns:    int32(getEnvInt("DATABASE_MAX_CONNS", 5)),
		DatabaseMaxConnLife: getEnvDuration("DATABASE_MAX_CONN_LIFETIME", 30*time.Minute),
		DatabaseMaxConnIdle: getEnvDuration("DATABASE_MAX_CONN_IDLE_TIME", 5*time.Minute),
		RedisURL:            getEnv("REDIS_URL", "redis://localhost:6379"),
		ServerPort:          getEnv("SERVER_PORT", "8080"),
		ServerHost:          getEnv("SERVER_HOST", "localhost"),
		Environment:         getEnv("ENVIRONMENT", "development"),
		InternalAPIToken:    getEnv("INTERNAL_API_TOKEN", ""),
		SpotifyClientID:     getEnv("SPOTIFY_CLIENT_ID", ""),
		SpotifyClientSecret: getEnv("SPOTIFY_CLIENT_SECRET", ""),
		SpotifyRedirectURI:  getEnv("SPOTIFY_REDIRECT_URI", ""),
		JWTSecret:           getEnv("JWT_SECRET", ""),
		CORSOrigins:         getEnv("CORS_ORIGINS", "http://localhost:5500"),
		Argon2Salt:          getEnv("ARGON2_SALT", "enigma-salt"),
		GraphEnabled:        getEnvBool("GRAPH_ENABLED", false),
		Neo4jURL:            getEnv("NEO4J_URL", "bolt://localhost:7687"),
		Neo4jUser:           getEnv("NEO4J_USER", "neo4j"),
		Neo4jPassword:       getEnv("NEO4J_PASSWORD", ""),
		GraphPollInterval:   getEnvDuration("GRAPH_POLL_INTERVAL", 2*time.Second),
		GraphBatchSize:      getEnvInt("GRAPH_BATCH_SIZE", 100),
	}

	if cfg.PostgresURL == "" {
		return nil, fmt.Errorf("POSTGRES_URL or POSTGRES_DB environment variable is required")
	}
	if cfg.JWTSecret == "" {
		return nil, fmt.Errorf("JWT_SECRET environment variable is required")
	}

	return cfg, nil
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}

func firstEnv(keys ...string) string {
	for _, key := range keys {
		if value, exists := os.LookupEnv(key); exists && value != "" {
			return value
		}
	}
	return ""
}

func getEnvInt(key string, defaultValue int) int {
	value := getEnv(key, "")
	if value == "" {
		return defaultValue
	}
	parsed, err := strconv.Atoi(value)
	if err != nil || parsed <= 0 {
		return defaultValue
	}
	return parsed
}

func getEnvBool(key string, defaultValue bool) bool {
	value := getEnv(key, "")
	if value == "" {
		return defaultValue
	}
	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return defaultValue
	}
	return parsed
}

func getEnvDuration(key string, defaultValue time.Duration) time.Duration {
	value := getEnv(key, "")
	if value == "" {
		return defaultValue
	}
	parsed, err := time.ParseDuration(value)
	if err != nil {
		return defaultValue
	}
	return parsed
}
