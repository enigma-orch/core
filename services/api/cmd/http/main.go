package main

import (
	"log/slog"

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

func main() {
	fx.New(
		config.Module,
		infra.Module,
		jwt.Module,
		repository.Module,
		service.Module,
		graph.Module,
		httpapi.Module,
		fx.WithLogger(func(log *slog.Logger) fxevent.Logger {
			return &fxevent.SlogLogger{Logger: log.With("component", "fx")}
		}),
	).Run()
}
