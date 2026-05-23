package service

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"time"

	"enigma/internal/domain"
	"enigma/internal/dto"
	"enigma/internal/repository"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
)

const (
	VisibilityPublic    = "public"
	VisibilityFollowers = "followers"
	VisibilityLinkOnly  = "link_only"
	VisibilityPrivate   = "private"
)

const profileOutfitLimit = 25

type PublicUser struct {
	ID          uuid.UUID `json:"id"`
	DisplayName string    `json:"display_name,omitempty"`
	AvatarURL   string    `json:"avatar_url,omitempty"`
}

type UserProfile struct {
	User           PublicUser          `json:"user"`
	FollowerCount  int64               `json:"follower_count"`
	FollowingCount int64               `json:"following_count"`
	IsFollowing    bool                `json:"is_following"`
	Outfits        []repository.Outfit `json:"outfits"`
}

type SharedOutfit struct {
	Share  repository.OutfitShare `json:"share"`
	Outfit repository.Outfit      `json:"outfit"`
}

type ShareOutfitInput struct {
	Visibility string
	ExpiresAt  *time.Time
}

func (s *Service) Follow(ctx context.Context, followerID, followeeID uuid.UUID) error {
	if followerID == followeeID {
		return fmt.Errorf("%w: cannot follow yourself", domain.ErrInvalidInput)
	}
	if _, err := s.repo.GetUserByID(ctx, followeeID); err != nil {
		return fmt.Errorf("checking followee: %w", err)
	}
	if err := s.repo.FollowUser(ctx, repository.FollowUserParams{
		FollowerID: followerID,
		FolloweeID: followeeID,
	}); err != nil {
		return fmt.Errorf("following user: %w", err)
	}
	s.log.InfoContext(ctx, "user followed", "actor", followerID, "target", followeeID)
	return nil
}

func (s *Service) Unfollow(ctx context.Context, followerID, followeeID uuid.UUID) error {
	if err := s.repo.UnfollowUser(ctx, repository.UnfollowUserParams{
		FollowerID: followerID,
		FolloweeID: followeeID,
	}); err != nil {
		return fmt.Errorf("unfollowing user: %w", err)
	}
	s.log.InfoContext(ctx, "user unfollowed", "actor", followerID, "target", followeeID)
	return nil
}

func (s *Service) GetFollowers(ctx context.Context, userID uuid.UUID, page Pagination) ([]repository.User, error) {
	users, err := s.repo.GetFollowers(ctx, repository.GetFollowersParams{
		FolloweeID: userID,
		Limit:      page.Limit,
		Offset:     page.Offset,
	})
	if err != nil {
		return nil, fmt.Errorf("getting followers: %w", err)
	}
	return users, nil
}

func (s *Service) GetFollowing(ctx context.Context, userID uuid.UUID, page Pagination) ([]repository.User, error) {
	users, err := s.repo.GetFollowing(ctx, repository.GetFollowingParams{
		FollowerID: userID,
		Limit:      page.Limit,
		Offset:     page.Offset,
	})
	if err != nil {
		return nil, fmt.Errorf("getting following: %w", err)
	}
	return users, nil
}

func (s *Service) SearchUsers(ctx context.Context, callerID uuid.UUID, query string, limit int32) ([]repository.User, error) {
	users, err := s.repo.SearchUsers(ctx, repository.SearchUsersParams{
		ID:      callerID,
		Column2: pgtype.Text{String: query, Valid: true},
		Limit:   limit,
	})
	if err != nil {
		return nil, fmt.Errorf("searching users: %w", err)
	}
	return users, nil
}

func (s *Service) GetUserProfile(ctx context.Context, viewerID, targetID uuid.UUID) (UserProfile, error) {
	snap, err := s.repo.GetProfileSnapshot(ctx, viewerID, targetID, profileOutfitLimit, 0)
	if err != nil {
		return UserProfile{}, fmt.Errorf("loading profile: %w", err)
	}

	pub := PublicUser{ID: snap.User.ID}
	if snap.User.DisplayName.Valid {
		pub.DisplayName = snap.User.DisplayName.String
	}
	if snap.User.AvatarUrl.Valid {
		pub.AvatarURL = snap.User.AvatarUrl.String
	}

	return UserProfile{
		User:           pub,
		FollowerCount:  snap.FollowersCount,
		FollowingCount: snap.FollowingCount,
		IsFollowing:    snap.IsFollowing,
		Outfits:        snap.Outfits,
	}, nil
}

func (s *Service) ShareOutfit(ctx context.Context, ownerID, outfitID uuid.UUID, input ShareOutfitInput) (repository.OutfitShare, error) {
	if input.Visibility == "" {
		input.Visibility = VisibilityPublic
	}
	if !validVisibility(input.Visibility) {
		return repository.OutfitShare{}, fmt.Errorf("%w: visibility must be public, followers, link_only, or private", domain.ErrInvalidInput)
	}

	var shareToken pgtype.Text
	if input.Visibility == VisibilityLinkOnly {
		token, err := generateToken()
		if err != nil {
			return repository.OutfitShare{}, fmt.Errorf("generating share token: %w", err)
		}
		shareToken = pgtype.Text{String: token, Valid: true}
	}

	var expiresAt pgtype.Timestamptz
	if input.ExpiresAt != nil {
		expiresAt = pgtype.Timestamptz{Time: *input.ExpiresAt, Valid: true}
	}

	var share repository.OutfitShare
	err := s.repo.WithTx(ctx, func(txRepo repository.SocialRepository) error {
		if _, err := txRepo.GetOutfitByID(ctx, repository.GetOutfitByIDParams{ID: outfitID, UserID: ownerID}); err != nil {
			return fmt.Errorf("getting outfit: %w", err)
		}
		out, err := txRepo.UpsertOutfitShare(ctx, repository.UpsertOutfitShareParams{
			OutfitID:   outfitID,
			OwnerID:    ownerID,
			Visibility: repository.VisibilityEnum(input.Visibility),
			ShareToken: shareToken,
			ExpiresAt:  expiresAt,
		})
		if err != nil {
			return fmt.Errorf("upserting outfit share: %w", err)
		}
		share = out
		return nil
	})
	if err != nil {
		return repository.OutfitShare{}, err
	}
	s.log.InfoContext(ctx, "outfit shared", "owner", ownerID, "outfit", outfitID, "visibility", input.Visibility)
	return share, nil
}

func (s *Service) GetShareByToken(ctx context.Context, token string) (SharedOutfit, error) {
	share, err := s.repo.GetOutfitShareByToken(ctx, pgtype.Text{String: token, Valid: true})
	if err != nil {
		return SharedOutfit{}, fmt.Errorf("getting share: %w", err)
	}

	outfit, err := s.repo.GetOutfitByID(ctx, repository.GetOutfitByIDParams{ID: share.OutfitID, UserID: share.OwnerID})
	if err != nil {
		return SharedOutfit{}, fmt.Errorf("getting shared outfit: %w", err)
	}

	return SharedOutfit{Share: share, Outfit: outfit}, nil
}

func (s *Service) GetFeed(ctx context.Context, userID uuid.UUID, page Pagination) ([]dto.FeedItem, error) {
	outfits, err := s.repo.GetFeedOutfits(ctx, repository.GetFeedOutfitsParams{
		FollowerID: userID,
		Limit:      page.Limit,
		Offset:     page.Offset,
	})
	if err != nil {
		return nil, fmt.Errorf("getting feed: %w", err)
	}

	// Collect unique owner IDs then fetch their public info.
	seen := map[uuid.UUID]bool{}
	var ownerIDs []uuid.UUID
	for _, o := range outfits {
		if !seen[o.UserID] {
			ownerIDs = append(ownerIDs, o.UserID)
			seen[o.UserID] = true
		}
	}
	owners := make(map[uuid.UUID]repository.User, len(ownerIDs))
	for _, id := range ownerIDs {
		u, err := s.repo.GetUserByID(ctx, id)
		if err != nil {
			continue
		}
		owners[id] = u
	}

	items := make([]dto.FeedItem, 0, len(outfits))
	for _, o := range outfits {
		item := dto.FeedItem{
			OutfitID:  o.ID.String(),
			OwnerID:   o.UserID.String(),
			WearCount: o.WearCount,
			CreatedAt: o.CreatedAt.Time.Format(time.RFC3339),
		}
		if o.Name.Valid {
			item.Name = o.Name.String
		}
		if o.PreviewImageUrl.Valid {
			item.PreviewImageURL = o.PreviewImageUrl.String
		}
		if o.Occasion.Valid {
			item.Occasion = o.Occasion.String
		}
		if o.Vibe.Valid {
			item.Vibe = o.Vibe.String
		}
		if u, ok := owners[o.UserID]; ok {
			if u.DisplayName.Valid {
				item.OwnerName = u.DisplayName.String
			}
			if u.AvatarUrl.Valid {
				item.OwnerAvatarURL = u.AvatarUrl.String
			}
		}
		items = append(items, item)
	}
	return items, nil
}

func validVisibility(v string) bool {
	switch v {
	case VisibilityPublic, VisibilityFollowers, VisibilityLinkOnly, VisibilityPrivate:
		return true
	}
	return false
}

func generateToken() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

