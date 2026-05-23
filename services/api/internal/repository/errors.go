package repository

import (
	"errors"

	"enigma/internal/domain"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
)

// translatePGError maps low-level pgx/pgconn errors to domain sentinels so
// callers can rely on errors.Is(err, domain.ErrXxx) regardless of driver
// specifics. Returns nil for nil input; passes through unrecognised errors.
func translatePGError(err error) error {
	if err == nil {
		return nil
	}
	if errors.Is(err, pgx.ErrNoRows) {
		return domain.ErrNotFound
	}
	var pgErr *pgconn.PgError
	if errors.As(err, &pgErr) {
		switch pgErr.Code {
		case "23505": // unique_violation
			return domain.ErrConflict
		case "23503", // foreign_key_violation
			"23514": // check_violation
			return domain.ErrInvalidInput
		}
	}
	return err
}
