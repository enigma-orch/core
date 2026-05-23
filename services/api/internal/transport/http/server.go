package httpapi

import (
	"context"
	"log/slog"
	"strconv"
	"time"

	"enigma/internal/domain"
	"enigma/internal/dto"
	"enigma/internal/graph"
	"enigma/internal/service"
	"enigma/internal/transport/http/middleware"
	pkgjwt "enigma/pkg/jwt"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

type ServerConfig struct {
	InternalAPIToken string
	Environment      string
}

type Server struct {
	db       *pgxpool.Pool
	redis    *redis.Client
	service  *service.Service
	verifier *pkgjwt.Verifier
	graph    *graphHandlers
	cfg      ServerConfig
}

func NewServer(
	db *pgxpool.Pool,
	redisClient *redis.Client,
	svc *service.Service,
	verifier *pkgjwt.Verifier,
	graphReader graph.Reader,
	cfg ServerConfig,
) *Server {
	return &Server{
		db:       db,
		redis:    redisClient,
		service:  svc,
		verifier: verifier,
		graph:    newGraphHandlers(graphReader),
		cfg:      cfg,
	}
}

func (s *Server) Register(app *fiber.App) {
	app.Get("/health/live", s.live)
	app.Get("/health/ready", s.ready)

	// Public — no auth
	app.Get("/share/:token", s.resolveShareToken)

	// Protected — Bearer JWT issued by FastAPI
	api := app.Group("/api/v1", middleware.RequireUser(s.verifier))
	api.Get("/users/search", s.searchUsers)
	api.Post("/users/:id/follow", s.followUser)
	api.Delete("/users/:id/follow", s.unfollowUser)
	api.Get("/users/:id/followers", s.listFollowers)
	api.Get("/users/:id/following", s.listFollowing)
	api.Get("/users/:id/profile", s.getUserProfile)
	api.Post("/outfits/:id/share", s.shareOutfit)
	api.Get("/feed", s.getFeed)

	s.graph.register(api.Group("/graph"))
}

// ─── Health ──────────────────────────────────────────────────────────────────

func (s *Server) live(c *fiber.Ctx) error {
	return ok(c, "API is live", fiber.Map{"status": "live"})
}

func (s *Server) ready(c *fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(c.UserContext(), 2*time.Second)
	defer cancel()

	checks, err := runHealthChecks(ctx, []healthCheck{
		{name: "postgres", run: s.db.Ping},
		{name: "redis", run: func(ctx context.Context) error { return s.redis.Ping(ctx).Err() }},
	})
	if err != nil {
		return err
	}
	return ok(c, "API is ready", fiber.Map{"status": "ready", "checks": checks})
}

// ─── Social handlers ──────────────────────────────────────────────────────────

func (s *Server) followUser(c *fiber.Ctx) error {
	followerID, followeeID, err := userAndParamID(c, "id")
	if err != nil {
		return err
	}
	if err := s.service.Follow(c.UserContext(), followerID, followeeID); err != nil {
		return err
	}
	return ok(c, "Followed", nil)
}

func (s *Server) unfollowUser(c *fiber.Ctx) error {
	followerID, followeeID, err := userAndParamID(c, "id")
	if err != nil {
		return err
	}
	if err := s.service.Unfollow(c.UserContext(), followerID, followeeID); err != nil {
		return err
	}
	return ok(c, "Unfollowed", nil)
}

func (s *Server) searchUsers(c *fiber.Ctx) error {
	callerID, err := requireUserID(c)
	if err != nil {
		return err
	}
	q := c.Query("q")
	if q == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"success": false, "message": "q is required"})
	}
	users, err := s.service.SearchUsers(c.UserContext(), callerID, q, 20)
	if err != nil {
		return err
	}
	return ok(c, "Users found", users)
}

func (s *Server) listFollowers(c *fiber.Ctx) error {
	targetID, err := parseParamID(c, "id")
	if err != nil {
		return err
	}
	users, err := s.service.GetFollowers(c.UserContext(), targetID, pagination(c))
	if err != nil {
		return err
	}
	return ok(c, "Followers retrieved", users)
}

func (s *Server) listFollowing(c *fiber.Ctx) error {
	targetID, err := parseParamID(c, "id")
	if err != nil {
		return err
	}
	users, err := s.service.GetFollowing(c.UserContext(), targetID, pagination(c))
	if err != nil {
		return err
	}
	return ok(c, "Following retrieved", users)
}

func (s *Server) getUserProfile(c *fiber.Ctx) error {
	targetID, err := parseParamID(c, "id")
	if err != nil {
		return err
	}
	viewerID, _ := middleware.UserID(c)
	profile, err := s.service.GetUserProfile(c.UserContext(), viewerID, targetID)
	if err != nil {
		return err
	}
	return ok(c, "Profile retrieved", profile)
}

func (s *Server) shareOutfit(c *fiber.Ctx) error {
	userID, outfitID, err := userAndParamID(c, "id")
	if err != nil {
		return err
	}
	var req shareOutfitRequest
	if err := bindAndValidate(c, &req); err != nil {
		return err
	}
	share, err := s.service.ShareOutfit(c.UserContext(), userID, outfitID, req.toService())
	if err != nil {
		return err
	}
	return created(c, "Outfit shared", share)
}

func (s *Server) resolveShareToken(c *fiber.Ctx) error {
	token := c.Params("token")
	if token == "" {
		return domain.ErrInvalidInput
	}
	result, err := s.service.GetShareByToken(c.UserContext(), token)
	if err != nil {
		return err
	}
	return ok(c, "Shared outfit retrieved", result)
}

func (s *Server) getFeed(c *fiber.Ctx) error {
	userID, err := requireUserID(c)
	if err != nil {
		return err
	}
	outfits, err := s.service.GetFeed(c.UserContext(), userID, pagination(c))
	if err != nil {
		return err
	}
	return ok(c, "Feed retrieved", outfits)
}

// ─── Logging middleware ─────────────────────────────────────────────────────

func RequestLogger(logger *slog.Logger) fiber.Handler {
	return func(c *fiber.Ctx) error {
		start := time.Now()
		err := c.Next()
		logger.InfoContext(c.UserContext(), "http request",
			"method", c.Method(),
			"path", c.Route().Path,
			"status", c.Response().StatusCode(),
			"duration_ms", time.Since(start).Milliseconds(),
			"request_id", c.GetRespHeader(fiber.HeaderXRequestID),
		)
		return err
	}
}

// ─── Response helpers ────────────────────────────────────────────────────────

func ok(c *fiber.Ctx, message string, data any) error {
	return c.JSON(dto.APIResponse{Success: true, Message: message, Data: data})
}

func created(c *fiber.Ctx, message string, data any) error {
	return c.Status(fiber.StatusCreated).JSON(dto.APIResponse{Success: true, Message: message, Data: data})
}

func requireUserID(c *fiber.Ctx) (uuid.UUID, error) {
	userID, ok := middleware.UserID(c)
	if !ok {
		return uuid.Nil, domain.ErrUnauthorized
	}
	return userID, nil
}

func userAndParamID(c *fiber.Ctx, name string) (uuid.UUID, uuid.UUID, error) {
	userID, err := requireUserID(c)
	if err != nil {
		return uuid.Nil, uuid.Nil, err
	}
	id, err := parseParamID(c, name)
	if err != nil {
		return uuid.Nil, uuid.Nil, err
	}
	return userID, id, nil
}

func parseParamID(c *fiber.Ctx, name string) (uuid.UUID, error) {
	id, err := uuid.Parse(c.Params(name))
	if err != nil {
		return uuid.Nil, domain.ErrInvalidInput
	}
	return id, nil
}

func optionalInt64Query(c *fiber.Ctx, key string) *int64 {
	value := c.Query(key)
	if value == "" {
		return nil
	}
	parsed, err := strconv.ParseInt(value, 10, 64)
	if err != nil {
		return nil
	}
	return &parsed
}

func pagination(c *fiber.Ctx) service.Pagination {
	return service.NormalizePagination(c.QueryInt("limit", 25), c.QueryInt("offset", 0))
}

var _ = optionalInt64Query // used by future handlers
