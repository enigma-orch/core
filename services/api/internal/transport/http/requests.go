package httpapi

import (
	"time"

	"enigma/internal/service"

	validation "github.com/go-ozzo/ozzo-validation/v4"
)

// validRFC3339 ensures a non-empty pointer parses as RFC3339.
var validRFC3339 = validation.NewStringRuleWithError(
	func(s string) bool {
		_, err := time.Parse(time.RFC3339, s)
		return err == nil
	},
	validation.NewError("validation_rfc3339", "must be a valid RFC3339 timestamp"),
)

type shareOutfitRequest struct {
	Visibility string  `json:"visibility"`
	ExpiresAt  *string `json:"expires_at"`
}

func (r shareOutfitRequest) Validate() error {
	return validation.ValidateStruct(&r,
		validation.Field(&r.Visibility,
			validation.In("", service.VisibilityPublic, service.VisibilityFollowers, service.VisibilityLinkOnly, service.VisibilityPrivate),
		),
		validation.Field(&r.ExpiresAt,
			validation.When(r.ExpiresAt != nil,
				validation.Required,
				validRFC3339,
			),
		),
	)
}

func (r shareOutfitRequest) toService() service.ShareOutfitInput {
	input := service.ShareOutfitInput{Visibility: r.Visibility}
	if r.ExpiresAt != nil {
		// Validate() already proved this parses.
		if t, err := time.Parse(time.RFC3339, *r.ExpiresAt); err == nil {
			input.ExpiresAt = &t
		}
	}
	return input
}

