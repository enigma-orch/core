package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	pkgjwt "enigma/pkg/jwt"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
)

const testSecret = "test-secret"

func issueToken(t *testing.T, sub string) string {
	t.Helper()
	tok := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.RegisteredClaims{
		Subject:   sub,
		IssuedAt:  jwt.NewNumericDate(time.Now()),
		ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Hour)),
	})
	signed, err := tok.SignedString([]byte(testSecret))
	if err != nil {
		t.Fatalf("signing token: %v", err)
	}
	return signed
}

func TestRequireUser(t *testing.T) {
	verifier := pkgjwt.NewVerifier(testSecret)
	validSub := "11111111-1111-1111-1111-111111111111"

	tests := []struct {
		name       string
		token      string
		wantStatus int
	}{
		{name: "missing token", wantStatus: fiber.StatusUnauthorized},
		{name: "garbage token", token: "not-a-jwt", wantStatus: fiber.StatusUnauthorized},
		{name: "valid token", token: issueToken(t, validSub), wantStatus: fiber.StatusOK},
		{name: "non-uuid sub", token: issueToken(t, "not-a-uuid"), wantStatus: fiber.StatusUnauthorized},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			app := fiber.New(fiber.Config{
				ErrorHandler: func(c *fiber.Ctx, err error) error {
					return c.SendStatus(fiber.StatusUnauthorized)
				},
			})
			app.Get("/protected", RequireUser(verifier), func(c *fiber.Ctx) error {
				if _, ok := UserID(c); !ok {
					t.Fatal("expected user ID in locals")
				}
				return c.SendStatus(fiber.StatusOK)
			})

			req := httptest.NewRequest(http.MethodGet, "/protected", nil)
			if tt.token != "" {
				req.Header.Set("Authorization", "Bearer "+tt.token)
			}
			resp, err := app.Test(req)
			if err != nil {
				t.Fatalf("app.Test() error = %v", err)
			}
			if resp.StatusCode != tt.wantStatus {
				t.Fatalf("status = %d, want %d", resp.StatusCode, tt.wantStatus)
			}
		})
	}
}

func TestRequireInternalToken(t *testing.T) {
	tests := []struct {
		name        string
		token       string
		environment string
		header      string
		wantStatus  int
	}{
		{name: "allows missing token outside production", environment: "development", wantStatus: fiber.StatusOK},
		{name: "rejects missing token in production", environment: "production", token: "secret", wantStatus: fiber.StatusUnauthorized},
		{name: "rejects wrong token", environment: "production", token: "secret", header: "wrong", wantStatus: fiber.StatusUnauthorized},
		{name: "allows matching token", environment: "production", token: "secret", header: "secret", wantStatus: fiber.StatusOK},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			app := fiber.New(fiber.Config{
				ErrorHandler: func(c *fiber.Ctx, err error) error {
					return c.SendStatus(fiber.StatusUnauthorized)
				},
			})
			app.Get("/internal", RequireInternalToken(tt.token, tt.environment), func(c *fiber.Ctx) error {
				return c.SendStatus(fiber.StatusOK)
			})

			req := httptest.NewRequest(http.MethodGet, "/internal", nil)
			if tt.header != "" {
				req.Header.Set("X-Internal-Token", tt.header)
			}
			resp, err := app.Test(req)
			if err != nil {
				t.Fatalf("app.Test() error = %v", err)
			}
			if resp.StatusCode != tt.wantStatus {
				t.Fatalf("status = %d, want %d", resp.StatusCode, tt.wantStatus)
			}
		})
	}
}
