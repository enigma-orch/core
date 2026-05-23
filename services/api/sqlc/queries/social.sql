-- name: GetUserByID :one
SELECT id, email, display_name, avatar_url, spotify_id, created_at, updated_at
FROM users
WHERE id = $1;

-- name: SearchUsers :many
SELECT id, email, display_name, avatar_url, spotify_id, created_at, updated_at
FROM users
WHERE id != $1
  AND (
    display_name ILIKE '%' || $2 || '%'
    OR email ILIKE '%' || $2 || '%'
  )
ORDER BY display_name
LIMIT $3;

-- name: FollowUser :exec
INSERT INTO follows (follower_id, followee_id)
VALUES ($1, $2)
ON CONFLICT DO NOTHING;

-- name: UnfollowUser :exec
DELETE FROM follows
WHERE follower_id = $1 AND followee_id = $2;

-- name: IsFollowing :one
SELECT EXISTS (
    SELECT 1 FROM follows
    WHERE follower_id = $1 AND followee_id = $2
) AS is_following;

-- name: CountFollowers :one
SELECT COUNT(*) FROM follows WHERE followee_id = $1;

-- name: CountFollowing :one
SELECT COUNT(*) FROM follows WHERE follower_id = $1;

-- name: GetFollowCounts :one
SELECT
    COALESCE(SUM(CASE WHEN f.followee_id = $1 THEN 1 ELSE 0 END), 0)::bigint AS followers_count,
    COALESCE(SUM(CASE WHEN f.follower_id = $1 THEN 1 ELSE 0 END), 0)::bigint AS following_count
FROM follows f
WHERE f.followee_id = $1 OR f.follower_id = $1;

-- name: GetFollowers :many
SELECT u.id, u.email, u.display_name, u.avatar_url, u.spotify_id, u.created_at, u.updated_at
FROM users u
JOIN follows f ON f.follower_id = u.id
WHERE f.followee_id = $1
ORDER BY f.created_at DESC
LIMIT $2 OFFSET $3;

-- name: GetFollowing :many
SELECT u.id, u.email, u.display_name, u.avatar_url, u.spotify_id, u.created_at, u.updated_at
FROM users u
JOIN follows f ON f.followee_id = u.id
WHERE f.follower_id = $1
ORDER BY f.created_at DESC
LIMIT $2 OFFSET $3;

-- name: UpsertOutfitShare :one
INSERT INTO outfit_shares (outfit_id, owner_id, visibility, share_token, expires_at)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (outfit_id) DO UPDATE
SET visibility   = EXCLUDED.visibility,
    share_token  = EXCLUDED.share_token,
    expires_at   = EXCLUDED.expires_at,
    updated_at   = now()
RETURNING id, outfit_id, owner_id, visibility, share_token, expires_at, created_at, updated_at;

-- name: GetOutfitShareByToken :one
SELECT id, outfit_id, owner_id, visibility, share_token, expires_at, created_at, updated_at
FROM outfit_shares
WHERE share_token = $1
  AND (expires_at IS NULL OR expires_at > now());

-- name: GetOutfitShareByOutfitID :one
SELECT id, outfit_id, owner_id, visibility, share_token, expires_at, created_at, updated_at
FROM outfit_shares
WHERE outfit_id = $1;

-- name: GetOutfitByID :one
SELECT id, user_id, name, preview_image_url, occasion, season, vibe, mood,
       source, rating, worn_at, wear_count, created_at, updated_at
FROM outfits
WHERE id = $1 AND user_id = $2;

-- name: GetPublicOutfitsByUser :many
SELECT o.id, o.user_id, o.name, o.preview_image_url, o.occasion, o.season,
       o.vibe, o.mood, o.source, o.rating, o.worn_at, o.wear_count, o.created_at, o.updated_at
FROM outfits o
JOIN outfit_shares os ON os.outfit_id = o.id
WHERE o.user_id = $1
  AND os.visibility = 'PUBLIC'
  AND (os.expires_at IS NULL OR os.expires_at > now())
ORDER BY o.created_at DESC
LIMIT $2 OFFSET $3;

-- name: GetFeedOutfits :many
SELECT o.id, o.user_id, o.name, o.preview_image_url, o.occasion, o.season,
       o.vibe, o.mood, o.source, o.rating, o.worn_at, o.wear_count, o.created_at, o.updated_at
FROM outfits o
JOIN outfit_shares os ON os.outfit_id = o.id
LEFT JOIN follows f ON f.followee_id = o.user_id AND f.follower_id = $1
WHERE os.visibility IN ('PUBLIC', 'FOLLOWERS')
  AND (os.expires_at IS NULL OR os.expires_at > now())
  AND o.user_id != $1
ORDER BY (f.follower_id IS NOT NULL) DESC, o.created_at DESC
LIMIT $2 OFFSET $3;
