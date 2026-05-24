# Onboarding

## Overview

The onboarding flow lets the app pre-populate selection screens from the server-defined catalog (vibes, color palettes, stores), then persist the user's choices in a single completion call. Catalog endpoints are unauthenticated so the app can fetch options before or during the login flow. The completion endpoint requires a Bearer JWT.

---

## Catalog endpoints

### GET /api/v1/onboarding/vibes

Returns the full list of style vibes the user can pick from.

**Auth:** None

**curl example**
```bash
curl http://localhost:8000/api/v1/onboarding/vibes
```

**Response — `200 OK`**
```json
[
  {
    "id": "uuid",
    "slug": "streetwear",
    "label": "Streetwear",
    "description": "Bold graphics, oversized fits, sneaker culture",
    "emoji": "🧢"
  }
]
```

**Seeded vibes**

| Slug | Label | Emoji |
|---|---|---|
| `streetwear` | Streetwear | 🧢 |
| `minimal` | Minimal | 🤍 |
| `old-money` | Old Money | 🏛️ |
| `y2k` | Y2K | ✨ |
| `dark-academia` | Dark Academia | 📚 |
| `sporty` | Sporty | ⚡ |
| `elegant` | Elegant | 🌹 |
| `bold` | Bold | 🔥 |
| `coastal` | Coastal | 🌊 |
| `edgy` | Edgy | 🖤 |
| `cottagecore` | Cottagecore | 🌸 |
| `business-casual` | Business Casual | 💼 |

---

### GET /api/v1/onboarding/colors

Returns the full list of color palettes. Each palette includes an ordered array of hex swatches the client can render as a color strip.

**Auth:** None

**curl example**
```bash
curl http://localhost:8000/api/v1/onboarding/colors
```

**Response — `200 OK`**
```json
[
  {
    "id": "uuid",
    "slug": "earth-tones",
    "label": "Earth Tones",
    "swatches": ["#8B5E3C", "#C49A6C", "#D4B896", "#E8D5B7"]
  }
]
```

**Seeded palettes**

| Slug | Label | Swatches |
|---|---|---|
| `monochrome` | Monochrome | `#000000` `#4a4a4a` `#9b9b9b` `#ffffff` |
| `earth-tones` | Earth Tones | `#8B5E3C` `#C49A6C` `#D4B896` `#E8D5B7` |
| `pastels` | Pastels | `#FFB3BA` `#FFDFBA` `#FFFFBA` `#BAFFC9` `#BAE1FF` |
| `neutrals` | Neutrals | `#F5F0EB` `#D4C5B0` `#A89880` `#6B5B4E` |
| `bold-primaries` | Bold Primaries | `#E63946` `#457B9D` `#2A9D8F` `#E9C46A` |
| `jewel-tones` | Jewel Tones | `#2E4057` `#048A81` `#8338EC` `#A4262C` |
| `warm-nudes` | Warm Nudes | `#C9956C` `#D4A57A` `#E8C4A0` `#F5DEB3` |
| `dark-moody` | Dark Moody | `#1A1A2E` `#16213E` `#2D4739` `#3D2B1F` |

---

### GET /api/v1/onboarding/stores

Returns the full list of stores the user can mark as preferred.

**Auth:** None

**curl example**
```bash
curl http://localhost:8000/api/v1/onboarding/stores
```

**Response — `200 OK`**
```json
[
  {
    "id": "uuid",
    "slug": "zara",
    "name": "Zara",
    "logo_url": null,
    "website_url": "https://www.zara.com"
  }
]
```

**Seeded stores**

| Slug | Name |
|---|---|
| `zara` | Zara |
| `hm` | H&M |
| `asos` | ASOS |
| `uniqlo` | Uniqlo |
| `nike` | Nike |
| `adidas` | Adidas |
| `pull-and-bear` | Pull&Bear |
| `mango` | Mango |
| `urban-outfitters` | Urban Outfitters |
| `free-people` | Free People |
| `shein` | SHEIN |
| `revolve` | Revolve |
| `nordstrom` | Nordstrom |
| `forever-21` | Forever 21 |
| `cos` | COS |

---

### GET /api/v1/onboarding/sizes

Returns all available sizes grouped by category. Use the `slug` values when submitting sizes via `POST /onboarding/complete`.

**Auth:** None

**curl example**
```bash
curl http://localhost:8000/api/v1/onboarding/sizes
```

**Response — `200 OK`**
```json
{
  "tops": [
    { "id": "uuid", "slug": "tops-s",   "label": "S"   },
    { "id": "uuid", "slug": "tops-m",   "label": "M"   },
    { "id": "uuid", "slug": "tops-l",   "label": "L"   },
    { "id": "uuid", "slug": "tops-xl",  "label": "XL"  },
    { "id": "uuid", "slug": "tops-2xl", "label": "2XL" }
  ],
  "bottoms": [
    { "id": "uuid", "slug": "bottoms-28", "label": "28" },
    { "id": "uuid", "slug": "bottoms-30", "label": "30" },
    "..."
  ],
  "shoes": [
    { "id": "uuid", "slug": "shoes-8",  "label": "8"  },
    { "id": "uuid", "slug": "shoes-9",  "label": "9"  },
    "..."
  ],
  "outerwear": [
    { "id": "uuid", "slug": "outerwear-s",   "label": "S"   },
    { "id": "uuid", "slug": "outerwear-m",   "label": "M"   },
    { "id": "uuid", "slug": "outerwear-l",   "label": "L"   },
    { "id": "uuid", "slug": "outerwear-xl",  "label": "XL"  },
    { "id": "uuid", "slug": "outerwear-2xl", "label": "2XL" }
  ]
}
```

**Seeded sizes**

| Category | Slugs | Labels |
|---|---|---|
| `tops` | `tops-s` · `tops-m` · `tops-l` · `tops-xl` · `tops-2xl` | S · M · L · XL · 2XL |
| `bottoms` | `bottoms-28` → `bottoms-44` | 28 · 29 · 30 · 31 · 32 · 33 · 34 · 36 · 38 · 40 · 42 · 44 |
| `shoes` | `shoes-8` → `shoes-28` | 8 through 28 |
| `outerwear` | `outerwear-s` · `outerwear-m` · `outerwear-l` · `outerwear-xl` · `outerwear-2xl` | S · M · L · XL · 2XL |

Items are returned sorted by `sort_order` within each category (i.e. smallest to largest), so the client can render them in order without additional sorting.

---

## POST /api/v1/onboarding/complete

Saves all choices made during onboarding to the user's profile in a single call. Every field is optional — only the provided fields are written.

**Auth:** `Bearer <access_token>`

**Content-Type:** `application/json`

**curl example**
```bash
curl -X POST http://localhost:8000/api/v1/onboarding/complete \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "vibes": ["streetwear", "minimal"],
    "preferred_colors": ["monochrome", "earth-tones"],
    "preferred_stores": ["zara", "asos", "uniqlo"],
    "display_name": "Alex",
    "location": "London, UK",
    "style_identity": "Quiet streetwear with a clean edge",
    "tops_size": "tops-m",
    "bottoms_size": "bottoms-32",
    "shoes_size": "shoes-42",
    "outerwear_size": "outerwear-l",
    "budget_min": 20,
    "budget_max": 200
  }'
```

### Request body

All fields are optional. Only supplied fields are written — omitted fields are left unchanged.

| Field | Type | Source | Description |
|---|---|---|---|
| `vibes` | `string[]` | `GET /onboarding/vibes` | Vibe slugs. Saved to `users.preferred_styles`. |
| `preferred_colors` | `string[]` | `GET /onboarding/colors` | Color palette slugs. Saved to `users.preferred_colors`. |
| `preferred_stores` | `string[]` | `GET /onboarding/stores` | Store slugs. Saved to `users.preferred_stores`. |
| `display_name` | `string \| null` | — | User's public display name. |
| `location` | `string \| null` | — | City or region — used for weather context in outfit suggestions. |
| `style_identity` | `string \| null` | — | Free-text style self-description, injected into outfit AI prompts. |
| `tops_size` | `string \| null` | `GET /onboarding/sizes` | Size slug from the `tops` group, e.g. `"tops-m"`, `"tops-xl"`. |
| `bottoms_size` | `string \| null` | `GET /onboarding/sizes` | Size slug from the `bottoms` group, e.g. `"bottoms-32"`, `"bottoms-34"`. |
| `shoes_size` | `string \| null` | `GET /onboarding/sizes` | Size slug from the `shoes` group, e.g. `"shoes-42"`, `"shoes-44"`. |
| `outerwear_size` | `string \| null` | `GET /onboarding/sizes` | Size slug from the `outerwear` group, e.g. `"outerwear-l"`. |
| `budget_min` | `integer \| null` | — | Minimum budget in USD (≥ 0). |
| `budget_max` | `integer \| null` | — | Maximum budget in USD (≥ 0). |

### Response — `200 OK`

Returns the full `UserMeOut` object with all profile fields, including the newly written preferences.

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "Alex",
  "avatar_url": null,
  "mood": "UNKNOWN",
  "location": "London, UK",
  "style_identity": "Quiet streetwear with a clean edge",
  "preferred_styles": ["streetwear", "minimal"],
  "preferred_colors": ["monochrome", "earth-tones"],
  "preferred_stores": ["zara", "asos", "uniqlo"],
  "budget_min": 20,
  "budget_max": 200,
  "tops_size": "tops-m",
  "bottoms_size": "bottoms-32",
  "shoes_size": "shoes-42",
  "outerwear_size": "outerwear-l",
  "spotify_id": null,
  "has_spotify": false,
  "has_google_calendar": false,
  "google_calendar_id": null,
  "created_at": "2026-05-24T00:00:00Z",
  "updated_at": "2026-05-24T00:00:00Z"
}
```

### Error responses

| Status | Meaning |
|---|---|
| `401` | Missing or invalid JWT |
| `404` | User record not found |

---

## How preferences flow downstream

| Field written | Where it's used |
|---|---|
| `preferred_styles` (vibes) | Shuffle scoring — vibe alignment boosts candidate score; outfit AI prompt includes style identity |
| `preferred_colors` | Future: filter/rank items and suggestions by palette |
| `preferred_stores` | Future: prioritise scraper results and store-product recommendations from selected retailers |
| `style_identity` | Injected into outfit compose AI prompt as context |
| `location` | Weather lookup for outfit context (`weather_svc.get_weather`) |
| Sizes | Returned in profile; future: filter store products by size |
| Budget | Returned in profile; future: filter store products by price range |
