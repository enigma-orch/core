package service

import (
	"log/slog"

	"enigma/internal/repository"
)

type Service struct {
	repo repository.SocialRepository
	log  *slog.Logger
}

func New(repo repository.SocialRepository, log *slog.Logger) *Service {
	return &Service{
		repo: repo,
		log:  log.With("component", "service"),
	}
}

type Pagination struct {
	Limit  int32
	Offset int32
}

func NormalizePagination(limit, offset int) Pagination {
	if limit <= 0 || limit > 100 {
		limit = 25
	}
	if offset < 0 {
		offset = 0
	}
	return Pagination{Limit: int32(limit), Offset: int32(offset)}
}
