package httpapi

import (
	"fmt"

	"enigma/internal/domain"

	"github.com/gofiber/fiber/v2"
)

// validatable is the optional contract a request DTO implements when it wants
// the binding helper to enforce field-level rules via ozzo-validation.
type validatable interface {
	Validate() error
}

// bindAndValidate parses the request body into out and runs Validate() when
// the type defines it. Any error is wrapped to ErrInvalidInput so the central
// error handler maps it to HTTP 400.
func bindAndValidate(c *fiber.Ctx, out any) error {
	if err := c.BodyParser(out); err != nil {
		return fmt.Errorf("%w: %s", domain.ErrInvalidInput, err.Error())
	}
	if v, ok := out.(validatable); ok {
		if err := v.Validate(); err != nil {
			return fmt.Errorf("%w: %s", domain.ErrInvalidInput, err.Error())
		}
	}
	return nil
}
