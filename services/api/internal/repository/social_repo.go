package repository

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ProfileSnapshot bundles everything GetUserProfile needs so the adapter can
// fetch it in one pgx.Batch round trip.
type ProfileSnapshot struct {
	User           User
	FollowersCount int64
	FollowingCount int64
	IsFollowing    bool
	Outfits        []Outfit
}

// SocialRepository is the persistence contract consumed by the service layer.
// The sqlc-generated *Queries satisfies most of it; sqlcSocialRepo wraps it to
// add transaction and batch helpers and to translate driver errors into
// domain sentinels.
type SocialRepository interface {
	GetUserByID(ctx context.Context, id uuid.UUID) (User, error)

	FollowUser(ctx context.Context, arg FollowUserParams) error
	UnfollowUser(ctx context.Context, arg UnfollowUserParams) error
	IsFollowing(ctx context.Context, arg IsFollowingParams) (bool, error)

	GetFollowers(ctx context.Context, arg GetFollowersParams) ([]User, error)
	GetFollowing(ctx context.Context, arg GetFollowingParams) ([]User, error)
	SearchUsers(ctx context.Context, arg SearchUsersParams) ([]User, error)

	GetPublicOutfitsByUser(ctx context.Context, arg GetPublicOutfitsByUserParams) ([]Outfit, error)
	GetFeedOutfits(ctx context.Context, arg GetFeedOutfitsParams) ([]Outfit, error)

	GetOutfitByID(ctx context.Context, arg GetOutfitByIDParams) (Outfit, error)
	GetOutfitShareByOutfitID(ctx context.Context, outfitID uuid.UUID) (OutfitShare, error)
	GetOutfitShareByToken(ctx context.Context, shareToken pgtype.Text) (OutfitShare, error)
	UpsertOutfitShare(ctx context.Context, arg UpsertOutfitShareParams) (OutfitShare, error)

	// GetProfileSnapshot fetches everything needed to render a user profile
	// in a single round trip. Pass uuid.Nil for viewerID when the caller is
	// anonymous; IsFollowing will be false in that case.
	GetProfileSnapshot(ctx context.Context, viewerID, targetID uuid.UUID, outfitLimit, outfitOffset int32) (ProfileSnapshot, error)

	// WithTx runs fn inside a transaction. The repository handed to fn
	// shares the same transaction; commit happens on a nil return.
	WithTx(ctx context.Context, fn func(SocialRepository) error) error

	// ClaimOutboxBatch returns up to limit unprocessed outbox rows under a
	// SKIP LOCKED guard, so multiple projector replicas can drain in parallel.
	ClaimOutboxBatch(ctx context.Context, limit int32) ([]ClaimOutboxBatchRow, error)
	// MarkOutboxProcessed timestamps the given rows so the next claim skips them.
	MarkOutboxProcessed(ctx context.Context, ids []int64) error
}

// batchSender narrows the pgx pool / tx surface to what GetProfileSnapshot
// needs. Both *pgxpool.Pool and pgx.Tx satisfy it.
type batchSender interface {
	SendBatch(ctx context.Context, b *pgx.Batch) pgx.BatchResults
}

type sqlcSocialRepo struct {
	q      *Queries
	pool   *pgxpool.Pool // nil when bound to a transaction
	sender batchSender
}

// NewSocialRepository builds the production adapter backed by pgx.
func NewSocialRepository(pool *pgxpool.Pool) SocialRepository {
	return &sqlcSocialRepo{q: New(pool), pool: pool, sender: pool}
}

// userFromIDRow lifts the slim GetUserByID projection into the full User model.
// Unselected columns stay at their zero value — callers that need them must
// load the full row separately.
func userFromIDRow(r GetUserByIDRow) User {
	return User{
		ID:          r.ID,
		Email:       r.Email,
		DisplayName: r.DisplayName,
		AvatarUrl:   r.AvatarUrl,
		SpotifyID:   r.SpotifyID,
		CreatedAt:   r.CreatedAt,
		UpdatedAt:   r.UpdatedAt,
	}
}

func usersFromFollowerRows(rows []GetFollowersRow) []User {
	users := make([]User, len(rows))
	for i, r := range rows {
		users[i] = User{
			ID:          r.ID,
			Email:       r.Email,
			DisplayName: r.DisplayName,
			AvatarUrl:   r.AvatarUrl,
			SpotifyID:   r.SpotifyID,
			CreatedAt:   r.CreatedAt,
			UpdatedAt:   r.UpdatedAt,
		}
	}
	return users
}

func usersFromFollowingRows(rows []GetFollowingRow) []User {
	users := make([]User, len(rows))
	for i, r := range rows {
		users[i] = User{
			ID:          r.ID,
			Email:       r.Email,
			DisplayName: r.DisplayName,
			AvatarUrl:   r.AvatarUrl,
			SpotifyID:   r.SpotifyID,
			CreatedAt:   r.CreatedAt,
			UpdatedAt:   r.UpdatedAt,
		}
	}
	return users
}

func usersFromSearchRows(rows []SearchUsersRow) []User {
	users := make([]User, len(rows))
	for i, r := range rows {
		users[i] = User{
			ID:          r.ID,
			Email:       r.Email,
			DisplayName: r.DisplayName,
			AvatarUrl:   r.AvatarUrl,
			SpotifyID:   r.SpotifyID,
			CreatedAt:   r.CreatedAt,
			UpdatedAt:   r.UpdatedAt,
		}
	}
	return users
}

func outfitFromByIDRow(r GetOutfitByIDRow) Outfit {
	return Outfit{
		ID:              r.ID,
		UserID:          r.UserID,
		Name:            r.Name,
		PreviewImageUrl: r.PreviewImageUrl,
		Occasion:        r.Occasion,
		Season:          r.Season,
		Vibe:            r.Vibe,
		Mood:            r.Mood,
		Source:          r.Source,
		Rating:          r.Rating,
		WornAt:          r.WornAt,
		WearCount:       r.WearCount,
		CreatedAt:       r.CreatedAt,
		UpdatedAt:       r.UpdatedAt,
	}
}

func outfitsFromPublicRows(rows []GetPublicOutfitsByUserRow) []Outfit {
	outfits := make([]Outfit, len(rows))
	for i, r := range rows {
		outfits[i] = Outfit{
			ID:              r.ID,
			UserID:          r.UserID,
			Name:            r.Name,
			PreviewImageUrl: r.PreviewImageUrl,
			Occasion:        r.Occasion,
			Season:          r.Season,
			Vibe:            r.Vibe,
			Mood:            r.Mood,
			Source:          r.Source,
			Rating:          r.Rating,
			WornAt:          r.WornAt,
			WearCount:       r.WearCount,
			CreatedAt:       r.CreatedAt,
			UpdatedAt:       r.UpdatedAt,
		}
	}
	return outfits
}

func outfitsFromFeedRows(rows []GetFeedOutfitsRow) []Outfit {
	outfits := make([]Outfit, len(rows))
	for i, r := range rows {
		outfits[i] = Outfit{
			ID:              r.ID,
			UserID:          r.UserID,
			Name:            r.Name,
			PreviewImageUrl: r.PreviewImageUrl,
			Occasion:        r.Occasion,
			Season:          r.Season,
			Vibe:            r.Vibe,
			Mood:            r.Mood,
			Source:          r.Source,
			Rating:          r.Rating,
			WornAt:          r.WornAt,
			WearCount:       r.WearCount,
			CreatedAt:       r.CreatedAt,
			UpdatedAt:       r.UpdatedAt,
		}
	}
	return outfits
}

func (r *sqlcSocialRepo) GetUserByID(ctx context.Context, id uuid.UUID) (User, error) {
	u, err := r.q.GetUserByID(ctx, id)
	if err != nil {
		return User{}, translatePGError(err)
	}
	return userFromIDRow(u), nil
}

func (r *sqlcSocialRepo) FollowUser(ctx context.Context, arg FollowUserParams) error {
	return r.runAtomic(ctx, func(q *Queries) error {
		if err := q.FollowUser(ctx, arg); err != nil {
			return err
		}
		return enqueue(ctx, q, EventFollowCreated, FollowEventPayload{
			FollowerID: arg.FollowerID,
			FolloweeID: arg.FolloweeID,
		})
	})
}

func (r *sqlcSocialRepo) UnfollowUser(ctx context.Context, arg UnfollowUserParams) error {
	return r.runAtomic(ctx, func(q *Queries) error {
		if err := q.UnfollowUser(ctx, arg); err != nil {
			return err
		}
		return enqueue(ctx, q, EventFollowDeleted, FollowEventPayload{
			FollowerID: arg.FollowerID,
			FolloweeID: arg.FolloweeID,
		})
	})
}

func (r *sqlcSocialRepo) IsFollowing(ctx context.Context, arg IsFollowingParams) (bool, error) {
	ok, err := r.q.IsFollowing(ctx, arg)
	return ok, translatePGError(err)
}

func (r *sqlcSocialRepo) GetFollowers(ctx context.Context, arg GetFollowersParams) ([]User, error) {
	rows, err := r.q.GetFollowers(ctx, arg)
	if err != nil {
		return nil, translatePGError(err)
	}
	return usersFromFollowerRows(rows), nil
}

func (r *sqlcSocialRepo) GetFollowing(ctx context.Context, arg GetFollowingParams) ([]User, error) {
	rows, err := r.q.GetFollowing(ctx, arg)
	if err != nil {
		return nil, translatePGError(err)
	}
	return usersFromFollowingRows(rows), nil
}

func (r *sqlcSocialRepo) SearchUsers(ctx context.Context, arg SearchUsersParams) ([]User, error) {
	rows, err := r.q.SearchUsers(ctx, arg)
	if err != nil {
		return nil, translatePGError(err)
	}
	return usersFromSearchRows(rows), nil
}

func (r *sqlcSocialRepo) GetPublicOutfitsByUser(ctx context.Context, arg GetPublicOutfitsByUserParams) ([]Outfit, error) {
	rows, err := r.q.GetPublicOutfitsByUser(ctx, arg)
	if err != nil {
		return nil, translatePGError(err)
	}
	return outfitsFromPublicRows(rows), nil
}

func (r *sqlcSocialRepo) GetFeedOutfits(ctx context.Context, arg GetFeedOutfitsParams) ([]Outfit, error) {
	rows, err := r.q.GetFeedOutfits(ctx, arg)
	if err != nil {
		return nil, translatePGError(err)
	}
	return outfitsFromFeedRows(rows), nil
}

func (r *sqlcSocialRepo) GetOutfitByID(ctx context.Context, arg GetOutfitByIDParams) (Outfit, error) {
	row, err := r.q.GetOutfitByID(ctx, arg)
	if err != nil {
		return Outfit{}, translatePGError(err)
	}
	return outfitFromByIDRow(row), nil
}

func (r *sqlcSocialRepo) GetOutfitShareByOutfitID(ctx context.Context, outfitID uuid.UUID) (OutfitShare, error) {
	s, err := r.q.GetOutfitShareByOutfitID(ctx, outfitID)
	return s, translatePGError(err)
}

func (r *sqlcSocialRepo) GetOutfitShareByToken(ctx context.Context, shareToken pgtype.Text) (OutfitShare, error) {
	s, err := r.q.GetOutfitShareByToken(ctx, shareToken)
	return s, translatePGError(err)
}

func (r *sqlcSocialRepo) ClaimOutboxBatch(ctx context.Context, limit int32) ([]ClaimOutboxBatchRow, error) {
	rows, err := r.q.ClaimOutboxBatch(ctx, limit)
	return rows, translatePGError(err)
}

func (r *sqlcSocialRepo) MarkOutboxProcessed(ctx context.Context, ids []int64) error {
	return translatePGError(r.q.MarkOutboxProcessed(ctx, ids))
}

func (r *sqlcSocialRepo) UpsertOutfitShare(ctx context.Context, arg UpsertOutfitShareParams) (OutfitShare, error) {
	var share OutfitShare
	err := r.runAtomic(ctx, func(q *Queries) error {
		out, err := q.UpsertOutfitShare(ctx, arg)
		if err != nil {
			return err
		}
		share = out
		// Treat PRIVATE visibility as a share revocation for downstream
		// projectors; everything else is a share update.
		event := EventOutfitShared
		if arg.Visibility == VisibilityEnumPRIVATE {
			event = EventOutfitShareRevoked
		}
		return enqueue(ctx, q, event, OutfitSharedPayload{
			OutfitID:   arg.OutfitID,
			OwnerID:    arg.OwnerID,
			Visibility: string(arg.Visibility),
		})
	})
	return share, err
}

// GetProfileSnapshot pipelines four queries into one round trip via pgx.Batch.
// When viewerID is uuid.Nil or equal to targetID the follow check is skipped.
func (r *sqlcSocialRepo) GetProfileSnapshot(
	ctx context.Context,
	viewerID, targetID uuid.UUID,
	outfitLimit, outfitOffset int32,
) (ProfileSnapshot, error) {
	checkFollow := viewerID != uuid.Nil && viewerID != targetID

	batch := &pgx.Batch{}
	batch.Queue(getUserByID, targetID)
	batch.Queue(getFollowCounts, targetID)
	if checkFollow {
		batch.Queue(isFollowing, viewerID, targetID)
	}
	batch.Queue(getPublicOutfitsByUser, targetID, outfitLimit, outfitOffset)

	br := r.sender.SendBatch(ctx, batch)
	defer br.Close()

	var snap ProfileSnapshot

	if err := br.QueryRow().Scan(
		&snap.User.ID,
		&snap.User.Email,
		&snap.User.DisplayName,
		&snap.User.AvatarUrl,
		&snap.User.SpotifyID,
		&snap.User.CreatedAt,
		&snap.User.UpdatedAt,
	); err != nil {
		return ProfileSnapshot{}, translatePGError(err)
	}

	if err := br.QueryRow().Scan(&snap.FollowersCount, &snap.FollowingCount); err != nil {
		return ProfileSnapshot{}, fmt.Errorf("scanning follow counts: %w", translatePGError(err))
	}

	if checkFollow {
		if err := br.QueryRow().Scan(&snap.IsFollowing); err != nil {
			return ProfileSnapshot{}, fmt.Errorf("scanning is_following: %w", translatePGError(err))
		}
	}

	outfitRows, err := br.Query()
	if err != nil {
		return ProfileSnapshot{}, fmt.Errorf("querying public outfits: %w", translatePGError(err))
	}
	defer outfitRows.Close()
	for outfitRows.Next() {
		var o Outfit
		if err := outfitRows.Scan(
			&o.ID, &o.UserID, &o.Name, &o.PreviewImageUrl, &o.Occasion, &o.Season,
			&o.Vibe, &o.Mood, &o.Source, &o.Rating, &o.WornAt, &o.WearCount,
			&o.CreatedAt, &o.UpdatedAt,
		); err != nil {
			return ProfileSnapshot{}, fmt.Errorf("scanning outfit row: %w", err)
		}
		snap.Outfits = append(snap.Outfits, o)
	}
	if err := outfitRows.Err(); err != nil {
		return ProfileSnapshot{}, translatePGError(err)
	}

	return snap, nil
}

// runAtomic ensures fn executes inside a transaction so that all the queries
// it issues commit (or roll back) together. When the receiver is already
// transaction-bound (pool == nil), fn reuses that transaction so callers can
// compose atomic writes.
func (r *sqlcSocialRepo) runAtomic(ctx context.Context, fn func(*Queries) error) error {
	if r.pool == nil {
		return translatePGError(fn(r.q))
	}
	tx, err := r.pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return fmt.Errorf("beginning tx: %w", translatePGError(err))
	}
	if err := fn(r.q.WithTx(tx)); err != nil {
		_ = tx.Rollback(ctx)
		return translatePGError(err)
	}
	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("committing tx: %w", translatePGError(err))
	}
	return nil
}

// WithTx runs fn inside a single pgx transaction. The repository handed to fn
// reuses the same *Queries via Queries.WithTx. Caller errors trigger a rollback;
// a nil return commits.
func (r *sqlcSocialRepo) WithTx(ctx context.Context, fn func(SocialRepository) error) error {
	if r.pool == nil {
		// Already inside a transaction — just nest the call.
		return fn(r)
	}
	tx, err := r.pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return fmt.Errorf("beginning tx: %w", translatePGError(err))
	}
	txRepo := &sqlcSocialRepo{q: r.q.WithTx(tx), pool: nil, sender: tx}
	if err := fn(txRepo); err != nil {
		_ = tx.Rollback(ctx)
		return err
	}
	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("committing tx: %w", translatePGError(err))
	}
	return nil
}
