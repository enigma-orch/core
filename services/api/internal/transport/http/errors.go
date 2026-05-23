package httpapi

import (
	"errors"
	"log/slog"

	"enigma/internal/domain"
	"enigma/internal/dto"

	"github.com/gofiber/fiber/v2"
	validation "github.com/go-ozzo/ozzo-validation/v4"
	"github.com/jackc/pgx/v5/pgconn"
)

// NewErrorHandler returns the central Fiber error handler. Handlers should
// return raw domain errors and let this mapper convert them to HTTP responses.
func NewErrorHandler(logger *slog.Logger) fiber.ErrorHandler {
	return func(c *fiber.Ctx, err error) error {
		status, message, payload := classify(err)
		if status >= fiber.StatusInternalServerError {
			logger.ErrorContext(c.UserContext(), "request failed",
				"error", err,
				"path", c.Path(),
				"method", c.Method(),
				"request_id", c.GetRespHeader(fiber.HeaderXRequestID),
			)
		}
		resp := dto.APIResponse{
			Success: false,
			Message: message,
			Error:   err.Error(),
		}
		if payload != nil {
			resp.Data = payload
		}
		return c.Status(status).JSON(resp)
	}
}

// classify is split out so it stays unit-testable without spinning a Fiber app.
func classify(err error) (status int, message string, payload any) {
	// Validation errors come back as a map of field -> error string.
	var verr validation.Errors
	if errors.As(err, &verr) {
		fields := make(map[string]string, len(verr))
		for k, v := range verr {
			fields[k] = v.Error()
		}
		return fiber.StatusBadRequest, "Invalid request", fields
	}

	// Postgres constraint errors that escape the repo layer.
	var pgErr *pgconn.PgError
	if errors.As(err, &pgErr) {
		switch pgErr.Code {
		case "23505":
			return fiber.StatusConflict, "Request conflicts with existing data", nil
		case "23503", "23514":
			return fiber.StatusBadRequest, "Invalid request", nil
		}
	}

	switch {
	case errors.Is(err, domain.ErrUnauthorized):
		return fiber.StatusUnauthorized, "Authentication is required", nil
	case errors.Is(err, domain.ErrInvalidInput):
		return fiber.StatusBadRequest, "Invalid request", nil
	case errors.Is(err, domain.ErrNotFound):
		return fiber.StatusNotFound, "Resource not found", nil
	case errors.Is(err, domain.ErrConflict):
		return fiber.StatusConflict, "Request conflicts with existing data", nil
	}

	return fiber.StatusInternalServerError, "An error occurred while processing your request", nil
}
