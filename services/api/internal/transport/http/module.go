package httpapi

import (
	"context"
	"log/slog"
	"net"

	"enigma/internal/config"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/gofiber/fiber/v2/middleware/requestid"
	"go.uber.org/fx"
)

// Module wires the HTTP transport layer: Fiber app, server, lifecycle hooks.
var Module = fx.Module("http",
	fx.Provide(
		serverConfigFrom,
		NewFiberApp,
		NewServer,
	),
	fx.Invoke(registerHTTPServer),
)

// serverConfigFrom extracts the transport-relevant subset of the global Config
// so the Server doesn't pull in the whole config surface.
func serverConfigFrom(cfg *config.Config) ServerConfig {
	return ServerConfig{
		InternalAPIToken: cfg.InternalAPIToken,
		Environment:      cfg.Environment,
	}
}

// NewFiberApp builds the Fiber app, attaches the central error handler and
// the standard middleware stack (recover, request-id, request logger, CORS).
func NewFiberApp(cfg *config.Config, logger *slog.Logger) *fiber.App {
	app := fiber.New(fiber.Config{
		ErrorHandler: NewErrorHandler(logger),
		Prefork:      cfg.Environment == "production",
	})
	app.Use(requestid.New())
	app.Use(recover.New())
	app.Use(RequestLogger(logger))
	app.Use(cors.New(cors.Config{
		AllowOrigins:     cfg.CORSOrigins,
		AllowHeaders:     "Origin,Content-Type,Accept,Authorization,X-Request-ID",
		AllowMethods:     "GET,POST,PUT,PATCH,DELETE",
		AllowCredentials: true,
	}))
	return app
}

func registerHTTPServer(
	lc fx.Lifecycle,
	cfg *config.Config,
	logger *slog.Logger,
	app *fiber.App,
	server *Server,
) {
	server.Register(app)

	addr := cfg.ServerHost + ":" + cfg.ServerPort
	lc.Append(fx.Hook{
		OnStart: func(ctx context.Context) error {
			ln, err := net.Listen("tcp", addr)
			if err != nil {
				return err
			}
			logger.InfoContext(ctx, "starting server", "addr", "http://"+addr)
			go func() {
				if err := app.Listener(ln); err != nil {
					logger.Error("server stopped", "error", err)
				}
			}()
			return nil
		},
		OnStop: func(ctx context.Context) error {
			logger.InfoContext(ctx, "stopping server")
			return app.ShutdownWithContext(ctx)
		},
	})
}
