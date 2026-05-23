package httpapi

import (
	"enigma/internal/domain"
	"enigma/internal/graph"

	"github.com/gofiber/fiber/v2"
)

// graphHandlers groups the graph-DB-backed endpoints. The reader is nil when
// GRAPH_ENABLED=false; in that case each handler short-circuits to 503.
type graphHandlers struct {
	reader graph.Reader
}

func newGraphHandlers(reader graph.Reader) *graphHandlers {
	return &graphHandlers{reader: reader}
}

func (g *graphHandlers) register(router fiber.Router) {
	router.Get("/suggested-follows", g.suggestedFollows)
	router.Get("/mutual/:id", g.mutualFollowers)
	router.Get("/taste-similar", g.tasteSimilar)
}

// guard returns true when the graph subsystem is enabled; otherwise it writes
// a 503 response and the handler should return immediately.
func (g *graphHandlers) guard(c *fiber.Ctx) bool {
	if g.reader != nil {
		return true
	}
	_ = c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
		"success": false,
		"message": "Graph subsystem disabled",
		"error":   "GRAPH_ENABLED is false",
	})
	return false
}

func (g *graphHandlers) suggestedFollows(c *fiber.Ctx) error {
	if !g.guard(c) {
		return nil
	}
	userID, err := requireUserID(c)
	if err != nil {
		return err
	}
	limit := c.QueryInt("limit", 20)
	out, err := g.reader.SuggestedFollows(c.UserContext(), userID, limit)
	if err != nil {
		return err
	}
	return ok(c, "Suggested follows retrieved", out)
}

func (g *graphHandlers) mutualFollowers(c *fiber.Ctx) error {
	if !g.guard(c) {
		return nil
	}
	viewerID, otherID, err := userAndParamID(c, "id")
	if err != nil {
		return err
	}
	if viewerID == otherID {
		return domain.ErrInvalidInput
	}
	limit := c.QueryInt("limit", 50)
	out, err := g.reader.MutualFollowers(c.UserContext(), viewerID, otherID, limit)
	if err != nil {
		return err
	}
	return ok(c, "Mutual followers retrieved", out)
}

func (g *graphHandlers) tasteSimilar(c *fiber.Ctx) error {
	if !g.guard(c) {
		return nil
	}
	userID, err := requireUserID(c)
	if err != nil {
		return err
	}
	limit := c.QueryInt("limit", 20)
	out, err := g.reader.TasteSimilarUsers(c.UserContext(), userID, limit)
	if err != nil {
		return err
	}
	return ok(c, "Taste-similar users retrieved", out)
}
