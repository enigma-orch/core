package repository

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/google/uuid"
)

// Outbox event types. Keep this list aligned with the
// social_outbox_event_type_check CHECK constraint.
const (
	EventFollowCreated     = "follow.created"
	EventFollowDeleted     = "follow.deleted"
	EventOutfitShared      = "outfit.shared"
	EventOutfitShareRevoked = "outfit.share_revoked"
)

// FollowEventPayload is shared by follow.created and follow.deleted.
type FollowEventPayload struct {
	FollowerID uuid.UUID `json:"follower_id"`
	FolloweeID uuid.UUID `json:"followee_id"`
}

// OutfitSharedPayload is emitted whenever a share is upserted.
type OutfitSharedPayload struct {
	OutfitID   uuid.UUID `json:"outfit_id"`
	OwnerID    uuid.UUID `json:"owner_id"`
	Visibility string    `json:"visibility"`
}

func enqueue(ctx context.Context, q *Queries, eventType string, payload any) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshaling %s payload: %w", eventType, err)
	}
	return q.EnqueueOutboxEvent(ctx, EnqueueOutboxEventParams{
		EventType: eventType,
		Payload:   data,
	})
}
