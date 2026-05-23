# Gallery API

Galleries are curated collections of outfits. A user can have multiple galleries, each optionally public. Public galleries appear in the discovery feed.

**Base path:** `/api/v1/galleries`

---

## Data Model

### Gallery object

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Gallery ID |
| `user_id` | UUID | Owner |
| `name` | string | Gallery name (1–100 chars) |
| `description` | string \| null | Optional description (max 500 chars) |
| `cover_image_url` | string \| null | Cover image. Auto-falls back to first outfit's `preview_image_url` on GET |
| `is_public` | boolean | Whether visible in public discovery |
| `outfit_count` | integer | Number of outfits in this gallery |
| `created_at` | ISO 8601 | |
| `updated_at` | ISO 8601 | |

### GalleryDetail object (includes outfits)

All Gallery fields plus:

| Field | Type | Description |
|---|---|---|
| `outfits` | OutfitSummary[] | Ordered list of outfits in the gallery |

### OutfitSummary object

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Outfit ID |
| `name` | string \| null | Outfit name |
| `preview_image_url` | string \| null | Generated try-on image URL |
| `occasion` | string \| null | |
| `season` | string \| null | |
| `vibe` | string \| null | |
| `mood` | string \| null | |
| `source` | string | Always `"ai_generated"` for composed outfits |
| `created_at` | ISO 8601 | |

---

## Endpoints

### Create gallery

```
POST /api/v1/galleries
```

**Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✅ | 1–100 chars |
| `description` | string | ❌ | Max 500 chars |
| `cover_image_url` | string | ❌ | Custom cover image URL |
| `is_public` | boolean | ❌ | Default `false` |

**Response** `201` — Gallery object

---

### List my galleries

```
GET /api/v1/galleries
```

Returns all galleries owned by the current user, newest first.

**Response** `200` — `Gallery[]`

---

### Discover public galleries

```
GET /api/v1/galleries/public?offset=0&limit=20
```

| Param | Type | Default | Description |
|---|---|---|---|
| `offset` | integer | 0 | Pagination offset |
| `limit` | integer | 20 | Max 100 |

**Response** `200` — `Gallery[]`

---

### Get gallery (with outfits)

```
GET /api/v1/galleries/{gallery_id}
```

Returns full gallery detail including ordered outfit list.  
Private galleries return `403` if requested by a non-owner.

**Response** `200` — GalleryDetail object

---

### Update gallery

```
PATCH /api/v1/galleries/{gallery_id}
```

All fields optional. Only send what needs to change.

**Body**

| Field | Type | Description |
|---|---|---|
| `name` | string | New name |
| `description` | string | New description |
| `cover_image_url` | string | Override cover image |
| `is_public` | boolean | Toggle visibility |

**Response** `200` — Gallery object

---

### Delete gallery

```
DELETE /api/v1/galleries/{gallery_id}
```

Deletes the gallery and all its outfit memberships. Does **not** delete the outfits themselves.

**Response** `204 No Content`

---

### Add outfit to gallery

```
POST /api/v1/galleries/{gallery_id}/outfits
```

**Body**

| Field | Type | Required |
|---|---|---|
| `outfit_id` | UUID | ✅ |

Outfits are appended to the end (position auto-increments).  
Returns `409` if the outfit is already in the gallery.

**Response** `201`

```json
{
  "gallery_id": "...",
  "outfit_id": "...",
  "position": 3
}
```

---

### Remove outfit from gallery

```
DELETE /api/v1/galleries/{gallery_id}/outfits/{outfit_id}
```

Removes the outfit from the gallery. Does **not** delete the outfit.

**Response** `204 No Content`

---

## Error Responses

| Status | Detail | Cause |
|---|---|---|
| `403` | `Not your gallery` | Attempt to modify another user's gallery |
| `403` | `This gallery is private` | Attempt to GET a private gallery as non-owner |
| `404` | `Gallery not found` | Invalid `gallery_id` |
| `404` | `Outfit not found` | Invalid `outfit_id` when adding |
| `404` | `Outfit not in this gallery` | Removing an outfit that isn't in the gallery |
| `409` | `Outfit already in this gallery` | Duplicate add attempt |

---

## Integration Notes

- Use `GET /api/v1/galleries` for the user's gallery list screen.
- Use `GET /api/v1/galleries/{id}` to render a gallery detail screen with the outfit grid.
- Use `GET /api/v1/galleries/public` for the discover/explore feed.
- `cover_image_url` on the detail endpoint falls back to the first outfit's `preview_image_url` automatically — safe to always render it.
- Outfit ordering within a gallery is by insertion order (`position`). Reordering is not yet supported.
- Deleting a gallery is non-destructive to outfits — the user's outfits remain intact.
