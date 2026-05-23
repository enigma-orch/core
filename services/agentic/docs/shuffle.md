# Shuffle — Personalized Outfit Suggestions

## Overview

`GET /api/v1/shuffle` returns a ranked list of outfit suggestions drawn from
the user's wardrobe. Each suggestion is a curated grouping of items (top +
bottom + optional shoes / outerwear / accessories) scored against the user's
taste, the current season, and the next upcoming calendar event.

When the hourly prefetch worker has already run for the user, the response
includes fully rendered **try-on preview images**, a **background color**, and
a **song suggestion** per outfit — with no latency cost at request time.
When no pre-generated suggestions exist yet (new user, first login), the
endpoint falls back to the same candidate ranking but without preview images.

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/shuffle` | Return outfit suggestions (fast path or live fallback) |
| `POST` | `/api/v1/shuffle/prefetch` | Trigger background pre-generation for the calling user |

---

## GET /api/v1/shuffle

### Query parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `occasion` | `string` | `null` | Force a specific occasion. When set, the pre-generated cache is bypassed and the live ranking runs with this occasion filter. Values: `casual` · `smart-casual` · `formal` · `party` · `activewear` · `streetwear` |
| `limit` | `int` | `5` | How many suggestions to return. Min 1, max 10. |
| `use_calendar` | `bool` | `true` | Derive occasion from the user's next Google Calendar event when no explicit `occasion` is given (live-fallback path only). |

### Response

**Status:** `200 OK`

```json
{
  "season": "spring",
  "taste_signal": "liked",
  "suggestions": [
    {
      "item_ids": ["uuid-1", "uuid-2", "uuid-3"],
      "items": [ ...ItemOut ],
      "score": 0.7843,
      "occasion": "casual",
      "season": "spring",
      "suggested_song": "Good Days — SZA",
      "preview_image_url": "https://your-server/api/v1/wardrobe/files/wardrobe/shuffle/abc.png",
      "background_color": "#3FDAE6",
      "event_context": null
    }
  ]
}
```

#### Top-level fields

| Field | Type | Description |
|---|---|---|
| `season` | `string` | Current season (`spring` · `summer` · `fall` · `winter`) |
| `taste_signal` | `string` | Source of the taste vector: `liked` (from liked outfits) · `worn` (from wear history) · `none` (no signal yet) |
| `suggestions` | `ShuffleSuggestion[]` | Ranked outfit suggestions |

#### `ShuffleSuggestion` fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `item_ids` | `UUID[]` | ❌ | IDs of the items in this outfit |
| `items` | `ItemOut[]` | ❌ | Full item objects (same schema as wardrobe endpoints) |
| `score` | `float` | ❌ | Composite ranking score (0–1, higher is better) |
| `occasion` | `string` | ✅ | Occasion this suggestion targets, or `null` for occasion-neutral |
| `season` | `string` | ✅ | Season this suggestion was generated for |
| `suggested_song` | `string` | ✅ | `"Track — Artist"` matched to the outfit mood (see Song Matching) |
| `preview_image_url` | `string` | ✅ | URL of the AI-generated try-on image. `null` in the live fallback path or if image generation failed. |
| `background_color` | `string` | ❌ | Hex color from the design palette chosen for this outfit (see Background Colors) |
| `event_context` | `EventContext` | ✅ | Calendar event that influenced this suggestion (live-fallback path only) |

### Response strategy

```
GET /shuffle
  │
  ├─ Does the user have unexpired pre-generated suggestions
  │  AND no explicit ?occasion= was passed?
  │      YES → return pre_rows from outfit_suggestions (with preview images)
  │      NO  ↓
  │
  └─ Live fallback
       1. Filter wardrobe items to current season
       2. Compute taste vector from liked / worn outfits
       3. Look up next Google Calendar event (if linked) → map to occasion
       4. Rank items by cosine similarity to taste vector within each category
       5. Assemble top + bottom (or dress) combos, layer optional pieces
       6. Score each combo: 0.6×similarity + 0.3×occasion_match − 0.1×recency
       7. Deduplicate (≥80% item overlap), return top K
       → No preview images in this path
```

### Error responses

| Status | Detail | Cause |
|---|---|---|
| `400` | `Wardrobe is empty — upload items first` | User has no items (live fallback path only) |
| `404` | `User not found` | JWT references a deleted user |

---

## POST /api/v1/shuffle/prefetch

Manually kicks off background pre-generation for the calling user. Returns
`202 Accepted` immediately — the work runs in the background.

The try-on image is generated using the **profile photo already stored on the
user's account** (`users.avatar_url`). The caller cannot supply a different
photo via this endpoint.

### When to call this

- After the user uploads their profile photo for the first time.
- After uploading new wardrobe items, to get fresh suggestions without waiting
  for the next hourly cron run.
- If the user manually asks to "refresh" their suggestions.

### Response

**Status:** `202 Accepted`

```json
{
  "status": "accepted",
  "message": "Shuffle pre-generation started in the background"
}
```

### Error responses

| Status | Detail | Cause |
|---|---|---|
| `400` | `No profile photo on file — upload one first...` | `users.avatar_url` is null; image generation would have nothing to work with |
| `404` | `User not found` | JWT references a deleted user |

---

## Candidate Ranking (both paths)

### Item bucketing

Items are grouped by `category`:

| Slot | Categories | Required |
|---|---|---|
| Top | `top` | ✅ (unless dress) |
| Bottom | `bottom` | ✅ (unless dress) |
| Dress | `dress` | Fills top + bottom |
| Shoes | `shoes` | Optional |
| Outerwear | `outerwear` | Optional (skipped for `activewear` / `party`) |
| Accessory | `accessory` · `bag` · `jewellery` | Optional |

### Ranking within each bucket

- If the user has a taste vector: sort by **cosine similarity** between the
  item's embedding and the taste vector.
- No taste vector: sort by `wear_count` descending (proxy for preference).
- Cap at 8 items per bucket to prevent combinatorial explosion.

### Scoring

```
score = 0.6 × cosine(combo_embedding, taste_vector)
      + 0.3 × occasion_match_ratio
      − 0.1 × recency_penalty
```

| Term | Description |
|---|---|
| `combo_embedding` | Mean of the embeddings of all items in the combo |
| `taste_vector` | Centroid of liked-outfit embeddings, or worn-outfit embeddings as fallback |
| `occasion_match_ratio` | Fraction of items whose `occasion` matches the target occasion |
| `recency_penalty` | Scaled `wear_count` (capped at 10 per item), averaged across combo |

---

## Background Colors

Each suggestion carries a `background_color` chosen from this palette based on
the outfit's vibe and occasion. The intent is a solid studio backdrop for the
try-on image.

| Hex | Color | Triggered by |
|---|---|---|
| `#DD4982` | Hot pink | `party` · `night out` · `bold` · `feminine` · `glam` |
| `#A281E9` | Soft purple | `formal` · `wedding` · `elegant` · `dreamy` · `mysterious` |
| `#3FDAE6` | Bright teal | `casual` · `fresh` · `summer` |
| `#FFC400` | Golden yellow | `activewear` · `sporty` · `energetic` |
| `#1E1E1E` | Near black | `streetwear` · `smart-casual` · `edgy` · `dark` |
| `#FAFAFA` | Off white | Default / minimal / clean |

Priority: **occasion** is checked first, then **vibe** keyword match, then the
default `#FAFAFA`.

---

## Song Matching

Each suggestion carries a `suggested_song` in `"Track — Artist"` format.

**If the user has Spotify connected:** the 20 most recently played tracks with
audio features are fetched. The track whose `(valence, energy)` pair is
closest (Euclidean distance) to the target profile for the outfit's mood is
chosen.

**Mood → target audio profile:**

| Mood | Valence | Energy |
|---|---|---|
| `happy` | 0.80 | 0.65 |
| `energetic` | 0.55 | 0.85 |
| `calm` | 0.65 | 0.28 |
| `relaxed` | 0.65 | 0.35 |
| `melancholic` | 0.25 | 0.38 |
| `sad` | 0.18 | 0.28 |
| `focused` | 0.50 | 0.52 |
| `angry` | 0.18 | 0.85 |

**Static fallback** (no Spotify, or no tracks with audio features): vibe
keywords are checked first, then the mood map.

| Mood | Fallback Song |
|---|---|
| `happy` | Happy — Pharrell Williams |
| `energetic` | Blinding Lights — The Weeknd |
| `calm` | Weightless — Marconi Union |
| `relaxed` | Sunset Lover — Petit Biscuit |
| `melancholic` | The Night We Met — Lord Huron |
| `sad` | Someone Like You — Adele |
| `focused` | Experience — Ludovico Einaudi |
| `angry` | Lose Yourself — Eminem |
| default | Good Days — SZA |

---

## Data Dependencies

| Dependency | Where |
|---|---|
| Item embeddings (768-dim) | `items.embedding` — written at upload time |
| Outfit embeddings | `outfits.embedding` — written at compose time |
| Outfit likes | `outfit_likes` table |
| Google Calendar token | `users.google_access_token` |
| Spotify tracks + audio features | `spotify_tracks` table, synced every 15 min |
| User profile photo | `users.avatar_url` — required for try-on image generation |
| Pre-generated suggestions | `outfit_suggestions` table — written by prefetch worker |
