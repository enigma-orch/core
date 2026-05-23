# Avatar Upload Endpoint

## Overview

Upload a profile picture for the authenticated user. The image is stored in RustFS and the `avatar_url` field on the `users` row is updated to the internal proxy URL. All consumers of `avatar_url` (social feeds, outfit likes, style pulse, shuffle try-on) read from the DB, so the new photo is reflected everywhere immediately.

---

## Request

**Method:** `POST`

**URL:** `http://localhost:8000/api/v1/users/me/avatar`

**Authorization:** `Bearer <access_token>`

**Content-Type:** `multipart/form-data`

**Form field:** `image` — single file.

Accepted file types: `image/jpeg`, `image/png`, `image/webp`  
Maximum file size: 5 MB

### curl example

```bash
curl -X POST http://localhost:8000/api/v1/users/me/avatar \
  -H "Authorization: Bearer <access_token>" \
  -F "image=@photo.jpg"
```

---

## Response

**Status:** `200 OK`

**Content-Type:** `application/json`

Returns the full updated `UserOut` object.

### Response fields

| Field | Type | Description |
|---|---|---|
| `id` | `string (UUID)` | User ID |
| `email` | `string \| null` | Email address |
| `display_name` | `string \| null` | Display name |
| `avatar_url` | `string \| null` | URL of the newly uploaded profile picture |
| `mood` | `string` | Current mood enum value |
| `spotify_id` | `string \| null` | Linked Spotify account ID |
| `google_calendar_id` | `string \| null` | Linked Google Calendar ID |
| `created_at` | `string (ISO 8601)` | Account creation timestamp |

### Example response

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "user@example.com",
  "display_name": "Alex",
  "avatar_url": "http://localhost:8000/api/v1/wardrobe/files/avatars/3fa85f64-5717-4562-b3fc-2c963f66afa6.jpg",
  "mood": "UNKNOWN",
  "spotify_id": "spotify123",
  "google_calendar_id": null,
  "created_at": "2026-05-01T10:00:00Z"
}
```

---

## Storage behaviour

The image is stored under the deterministic key `avatars/{user_id}.{ext}`. Re-uploading a new photo overwrites the previous object — no orphaned files accumulate. The file is served through the existing wardrobe file proxy at `/api/v1/wardrobe/files/{key}`.

---

## Error responses

| Status | Meaning |
|---|---|
| `400` | Empty file |
| `401` | Missing or invalid JWT |
| `404` | User record not found |
| `413` | File exceeds 5 MB |
| `415` | Unsupported file type (not JPEG, PNG, or WEBP) |

```json
{ "detail": "<reason>" }
```

---

## Where `avatar_url` is consumed

Every consumer reads `avatar_url` directly from the `users` DB row — no caching layer. Uploading a new avatar is reflected immediately in:

| Location | Context |
|---|---|
| `GET /social/follows` | Followee avatars in the follows list |
| `GET /social/style-pulse` | Friend avatars in the style feed |
| `GET /home` (home feed) | Friend avatars in outfit previews |
| `GET /outfits/:id/likes` | Avatars on outfit likes |
| `POST /shuffle/prefetch` | Base image for AI outfit try-on — requires `avatar_url` to be set |
| Shuffle prefetch worker | Hourly cron try-on generation |
