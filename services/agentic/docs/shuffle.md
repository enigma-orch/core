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

## Mobile integration guide

### Prerequisites — what must be true before shuffle works

| # | Requirement | How to satisfy | Endpoint |
|---|---|---|---|
| 1 | User account exists | Guest or OAuth login | `POST /auth/guest` · `GET /auth/spotify` · `POST /auth/google` |
| 2 | At least 1 wardrobe item uploaded | Upload clothing photos | `POST /wardrobe/upload` |
| 3 | Items have both a top and a bottom (or at least one dress) | Upload the right categories | same |
| 4 | Profile photo uploaded | Required **only** for try-on preview images via `/shuffle/prefetch` | `PATCH /users/me/avatar` |

Requirements 1–3 are hard blockers — the endpoint returns `400` without them.  
Requirement 4 is only needed for the richer pre-generated path (with try-on images); `GET /shuffle` works without it but returns `null` for `preview_image_url`.

---

### Recommended first-launch sequence

```
1. Login  →  POST /auth/guest  (or Spotify / Google)
             ↳ store access_token + refresh_token

2. Onboarding  →  GET /onboarding/vibes, /colors, /stores   (show selection screens)
               →  POST /onboarding/complete                  (save choices)

3. Wardrobe setup  →  PATCH /users/me/avatar    (upload profile photo)
                   →  POST /wardrobe/upload      (upload clothing items, 1+ tops + 1+ bottoms)

4. Prime suggestions  →  POST /shuffle/prefetch   (fires background try-on generation)
                         ↳ returns 202 immediately — poll or wait before fetching

5. Fetch suggestions  →  GET /shuffle
```

After step 4, try-on images are usually ready within 2–5 minutes depending on wardrobe size. The app can call `GET /shuffle` optimistically before they're ready — it will return item groupings and metadata immediately with `preview_image_url: null`, and the images will appear on subsequent calls once generation completes.

---

### When to call each endpoint

| Trigger | Action |
|---|---|
| App foreground / home tab open | `GET /shuffle` (use cached response if < 1 hour old) |
| User uploads new wardrobe item | `POST /shuffle/prefetch` then refresh suggestions |
| User uploads profile photo | `POST /shuffle/prefetch` (first time avatar is set) |
| User taps "Refresh" | `POST /shuffle/prefetch` → wait for 202 → re-fetch after delay |
| User picks an occasion (e.g. "party tonight") | `GET /shuffle?occasion=party` |
| User's calendar has an event today | Handled server-side automatically when `use_calendar=true` (default) |

---

### Handling the two response paths

Always check `preview_image_url` per suggestion — it can be `null` even in a 200 response.

```
suggestion.preview_image_url != null
  → show try-on image as card hero

suggestion.preview_image_url == null
  → fall back to a collage of suggestion.items[*].clean_image_url
    (the individual clothing item images, background-removed)
```

`taste_signal` tells you the quality of personalisation to show in the UI:

| `taste_signal` | Meaning | Suggested UI hint |
|---|---|---|
| `liked` | Ranked from outfits the user has liked | — (best signal, no hint needed) |
| `worn` | Ranked from wear history | "Based on what you've been wearing" |
| `none` | No signal yet — random-ish ranking | "Add more items or like some outfits to personalise" |

---

### Occasions

Valid values for the `?occasion=` query param (and what triggers them automatically from calendar events):

| Value | Triggered by event keywords |
|---|---|
| `casual` | _(default when no event matches)_ |
| `smart-casual` | meeting · office · work · presentation · standup · date · dinner |
| `formal` | interview · wedding · gala |
| `party` | party · birthday · club · night out |
| `activewear` | gym · workout · run · yoga · pilates · training |
| `streetwear` | _(manual override only)_ |

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/shuffle` | ✅ | Return outfit suggestions (fast path or live fallback) |
| `POST` | `/api/v1/shuffle/prefetch` | ✅ | Trigger background pre-generation for the calling user |

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

## Data dependencies

| Dependency | Where | Required for |
|---|---|---|
| Item embeddings (768-dim) | `items.embedding` — written at upload time | Taste-vector ranking |
| Outfit embeddings | `outfits.embedding` — written at compose time | Taste vector |
| Outfit likes | `outfit_likes` table | `taste_signal = liked` |
| Google Calendar token | `users.google_access_token` | Automatic occasion inference |
| Spotify tracks + audio features | `spotify_tracks` table, synced every 24 h | Song matching + music taste boost |
| Spotify top artists / playlists | Fetched live from Spotify API when user has token | Genre → vibe score boost (stub — coming soon) |
| User profile photo | `users.avatar_url` | Try-on image generation via `/shuffle/prefetch` |
| Pre-generated suggestions | `outfit_suggestions` table — written by prefetch worker | Fast path (with preview images) |

### Constraints summary for mobile

| Constraint | Consequence if violated |
|---|---|
| No wardrobe items | `400 Wardrobe is empty` |
| Items exist but no top+bottom combo (and no dress) | Returns 0 suggestions |
| No profile photo (`avatar_url` is null) | `POST /shuffle/prefetch` returns `400`; `GET /shuffle` still works but `preview_image_url` is always `null` |
| Spotify not linked | Song matching falls back to static curated list; no music taste boost |
| Google Calendar not linked | Occasion not inferred automatically; pass `?occasion=` manually or omit |
| Pre-generated suggestions expired (> 24 h old) | Falls back to live ranking — same metadata, no preview images until next prefetch |
