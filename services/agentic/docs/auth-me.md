# GET /auth/me

## Overview

Returns the complete user context in a single request. Use this on app launch to hydrate the full user state — identity, avatar, mood, resolved style preferences (vibes, color palettes, stores with full objects), sizing, budget, and integration status.

**Auth:** `Bearer <access_token>` required.

---

## Request

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

## Response — `200 OK`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "user@example.com",
  "display_name": "Alex",
  "avatar_url": "http://localhost:8000/api/v1/wardrobe/files/avatars/3fa85f64.../photo.jpg",
  "mood": "ENERGETIC",

  "vibes": [
    {
      "id": "uuid",
      "slug": "streetwear",
      "label": "Streetwear",
      "description": "Bold graphics, oversized fits, sneaker culture",
      "emoji": "🧢"
    },
    {
      "id": "uuid",
      "slug": "minimal",
      "label": "Minimal",
      "description": "Clean lines, neutral palette, quiet confidence",
      "emoji": "🤍"
    }
  ],

  "color_palettes": [
    {
      "id": "uuid",
      "slug": "monochrome",
      "label": "Monochrome",
      "swatches": ["#000000", "#4a4a4a", "#9b9b9b", "#ffffff"]
    }
  ],

  "stores": [
    {
      "id": "uuid",
      "slug": "zara",
      "name": "Zara",
      "logo_url": null,
      "website_url": "https://www.zara.com"
    },
    {
      "id": "uuid",
      "slug": "asos",
      "name": "ASOS",
      "logo_url": null,
      "website_url": "https://www.asos.com"
    }
  ],

  "preferred_styles": ["streetwear", "minimal"],
  "preferred_colors": ["monochrome"],
  "preferred_stores": ["zara", "asos"],

  "location": "London, UK",
  "style_identity": "Quiet streetwear with a clean edge",

  "tops_size": "M",
  "bottoms_size": "32",
  "shoes_size": "42",
  "outerwear_size": "M",

  "budget_min": 20,
  "budget_max": 200,

  "spotify_id": "spotify_user_123",
  "has_spotify": true,
  "has_google_calendar": false,
  "google_calendar_id": null,

  "created_at": "2026-05-24T00:00:00Z",
  "updated_at": "2026-05-24T12:00:00Z"
}
```

---

## Response fields

### Identity

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | User ID — use this as the canonical identifier everywhere |
| `email` | `string \| null` | Email. `null` for guest users or Spotify users who didn't share their email |
| `display_name` | `string \| null` | Display name |
| `avatar_url` | `string \| null` | Full URL of the profile photo served via the internal file proxy. `null` if no photo uploaded yet |
| `mood` | `string` | Current mood enum: `HAPPY` · `SAD` · `ENERGETIC` · `CALM` · `MELANCHOLIC` · `ANGRY` · `RELAXED` · `FOCUSED` · `UNKNOWN` |

### Style preferences — resolved objects

These are the user's onboarding selections resolved to full catalog objects. **Order matches the order the user selected them.**

| Field | Type | Description |
|---|---|---|
| `vibes` | `Vibe[]` | Full vibe objects for each selected style vibe |
| `color_palettes` | `ColorPalette[]` | Full palette objects including hex swatches |
| `stores` | `Store[]` | Full store objects including website URL |

#### `Vibe`
| Field | Type |
|---|---|
| `id` | `UUID` |
| `slug` | `string` |
| `label` | `string` |
| `description` | `string \| null` |
| `emoji` | `string \| null` |

#### `ColorPalette`
| Field | Type |
|---|---|
| `id` | `UUID` |
| `slug` | `string` |
| `label` | `string` |
| `swatches` | `string[]` — ordered hex codes |

#### `Store`
| Field | Type |
|---|---|
| `id` | `UUID` |
| `slug` | `string` |
| `name` | `string` |
| `logo_url` | `string \| null` |
| `website_url` | `string \| null` |

### Style preferences — raw slugs

Included alongside the resolved objects for fast membership checks without iterating.

| Field | Type |
|---|---|
| `preferred_styles` | `string[] \| null` |
| `preferred_colors` | `string[] \| null` |
| `preferred_stores` | `string[] \| null` |

### Profile

| Field | Type | Description |
|---|---|---|
| `location` | `string \| null` | City / location string. Used for weather context in outfit composition |
| `style_identity` | `string \| null` | Free-text self-description injected into outfit AI prompts |

### Sizing

| Field | Type |
|---|---|
| `tops_size` | `string \| null` |
| `bottoms_size` | `string \| null` |
| `shoes_size` | `string \| null` |
| `outerwear_size` | `string \| null` |

### Budget

| Field | Type | Description |
|---|---|---|
| `budget_min` | `integer \| null` | Minimum budget (whole currency units) |
| `budget_max` | `integer \| null` | Maximum budget |

### Integrations

| Field | Type | Description |
|---|---|---|
| `spotify_id` | `string \| null` | Spotify user ID. `null` if not linked |
| `has_spotify` | `bool` | Shorthand for `spotify_id != null` |
| `has_google_calendar` | `bool` | Whether a Google Calendar token is on file |
| `google_calendar_id` | `string \| null` | Active calendar ID (usually `"primary"`) |

### Timestamps

| Field | Type |
|---|---|
| `created_at` | `ISO 8601` |
| `updated_at` | `ISO 8601` |

---

## Error responses

| Status | Detail | Cause |
|---|---|---|
| `401` | `Token expired` | Access token has expired — use `POST /auth/refresh` to rotate |
| `401` | `Invalid token` | Malformed or tampered token |
| `401` | `User not found — please log in again` | Token valid but user was deleted |
| `404` | `User not found` | User record missing |

---

## Usage notes

- **Call on app launch** after loading a stored access token. One request gives you everything needed to render the home screen, profile tab, and personalised shuffle.
- **`avatar_url` can be `null`** on first login before the user uploads a photo. Gate the shuffle prefetch call on this field being non-null (prefetch requires an avatar for try-on image generation).
- **`vibes`, `color_palettes`, `stores` are empty arrays** (not `null`) if the user skipped onboarding or hasn't completed it yet — safe to render as empty selection states.
- **`has_spotify: false`** means song suggestions in shuffle fall back to the curated static list and music taste boosting is inactive.
- **`mood`** is derived from the user's recent Spotify listening (updated every 24 h sync). Use it to personalise greeting copy or UI theming.
