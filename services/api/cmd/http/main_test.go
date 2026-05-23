package main

import (
	"log/slog"
	"testing"

	"enigma/internal/config"
	"enigma/internal/graph"
	"enigma/internal/infra"
	"enigma/internal/repository"
	"enigma/internal/service"
	httpapi "enigma/internal/transport/http"
	"enigma/pkg/jwt"

	"go.uber.org/fx"
	"go.uber.org/fx/fxevent"
)

// TestFxGraph confirms the application graph wires without missing or
// duplicate providers. It does not actually start the server.
func TestFxGraph(t *testing.T) {
	err := fx.ValidateApp(
		config.Module,
		infra.Module,
		jwt.Module,
		repository.Module,
		service.Module,
		graph.Module,
		httpapi.Module,
		fx.WithLogger(func(*slog.Logger) fxevent.Logger {
			return fxevent.NopLogger
		}),
	)
	if err != nil {
		t.Fatalf("fx graph is invalid: %v", err)
	}
}
