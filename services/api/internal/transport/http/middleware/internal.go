package middleware

import (
	"crypto/subtle"

	"enigma/internal/domain"

	"github.com/gofiber/fiber/v2"
)

func RequireInternalToken(token string, environment string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		if token == "" && environment != "production" {
			return c.Next()
		}
		if token == "" {
			return domain.ErrUnauthorized
		}
		provided := c.Get("X-Internal-Token")
		if subtle.ConstantTimeCompare([]byte(provided), []byte(token)) != 1 {
			return domain.ErrUnauthorized
		}
		return c.Next()
	}
}
