package repository

import "go.uber.org/fx"

// Module wires the persistence layer. Consumers receive a SocialRepository,
// not the sqlc *Queries directly.
var Module = fx.Module("repository",
	fx.Provide(NewSocialRepository),
)
