package jwt

import (
	"enigma/internal/config"

	"go.uber.org/fx"
)

// Module provides the *Verifier wired with the JWT secret from config.
var Module = fx.Module("jwt",
	fx.Provide(func(cfg *config.Config) *Verifier {
		return NewVerifier(cfg.JWTSecret)
	}),
)
