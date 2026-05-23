package middleware

import (
	"strings"

	"enigma/internal/domain"
	pkgjwt "enigma/pkg/jwt"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

const UserIDLocal = "user_id"

// RequireUser validates the Bearer JWT issued by the FastAPI service. The
// verifier must be constructed once at startup so the HMAC secret is not
// reloaded per request.
func RequireUser(verifier *pkgjwt.Verifier) fiber.Handler {
	return func(c *fiber.Ctx) error {
		raw := strings.TrimPrefix(c.Get("Authorization"), "Bearer ")
		if raw == "" {
			return domain.ErrUnauthorized
		}
		claims, err := verifier.Parse(raw)
		if err != nil {
			return domain.ErrUnauthorized
		}
		sub, err := pkgjwt.UserID(claims)
		if err != nil {
			return domain.ErrUnauthorized
		}
		userID, err := uuid.Parse(sub)
		if err != nil {
			return domain.ErrUnauthorized
		}
		c.Locals(UserIDLocal, userID)
		return c.Next()
	}
}

func UserID(c *fiber.Ctx) (uuid.UUID, bool) {
	switch v := c.Locals(UserIDLocal).(type) {
	case uuid.UUID:
		return v, true
	default:
		return uuid.Nil, false
	}
}
