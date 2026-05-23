# Shuffle Algorithm — System Design

## Overview

The shuffle algorithm generates personalized outfit suggestions for the user by combining signals from four sources: current season/weather, upcoming calendar events, liked outfits, and the user's existing wardrobe items. Each candidate outfit is scored, ranked, and rendered as a virtual try-on image using the compose pipeline.

---

## Input Signals

### 1. Current Season
- Derived from the current date (no external API needed).
- Used to filter items and outfits tagged for that season.
- Mapping: Dec–Feb → `winter`, Mar–May → `spring`, Jun–Aug → `summer`, Sep–Nov → `fall`.

### 2. Upcoming Calendar Events (Google Calendar)
- Fetch next 7 days of events from the user's linked Google Calendar.
- Map event title/description keywords to occasion tags:

| Keywords | Occasion |
|---|---|
| meeting, interview, office, work | `smart-casual` or `formal` |
| party, birthday, wedding, gala | `party` |
| gym, workout, run, yoga | `activewear` |
| date, dinner, night out | `smart-casual` |
| anything else | `casual` |

- Multiple events produce multiple occasion slots — shuffle generates one outfit per relevant event.

### 3. Liked Outfits (Taste Vector)
- Collect all outfits the user has liked (`outfit_likes` table).
- Extract their embeddings (768-dim vectors already stored in DB).
- Compute the **centroid** (mean vector) → this is the user's current taste vector.
- Used for cosine similarity scoring against candidate outfits.

### 4. Wardrobe Items
- All items belonging to the user from the `items` table.
- Already have embeddings, category, season, occasion, vibe, mood stored.

---

## Candidate Generation

### Step 1 — Filter by context
- Keep only items whose `season` array includes the current season (or is empty/null = all-season).
- If an upcoming event has a mapped occasion, further filter or prioritize items matching that occasion.

### Step 2 — Assemble outfit candidates
Build outfit combinations following this slot structure:

```
[required] 1 × top       (category = top)
[required] 1 × bottom    (category = bottom | dress)
[optional] 1 × shoes     (category = shoes)
[optional] 1 × outerwear (category = outerwear)
[optional] 1 × accessory (category = accessory | bag | jewellery)
```

- For dresses: top + bottom slots are filled by a single dress item.
- Limit combinations to avoid explosion: top 5 items per slot × slot count = manageable candidate set.
- Each unique combination is one candidate outfit.

### Step 3 — Score each candidate

```
score = (α × similarity) + (β × occasion_match) − (γ × recency_penalty)
```

| Term | Weight | Description |
|---|---|---|
| `similarity` | α = 0.6 | Cosine similarity between the candidate's combined item embeddings and the user's taste vector |
| `occasion_match` | β = 0.3 | 1.0 if all items match the upcoming event's occasion, 0.5 if partial, 0.0 if none |
| `recency_penalty` | γ = 0.1 | Scaled by how recently this exact combination (or constituent items) was worn. Uses `wear_count` and `last_worn_at` on items |

**Combined embedding** of a candidate: mean of all member item embeddings.

### Step 4 — Rank and deduplicate
- Sort candidates by score descending.
- Remove near-duplicates: if two candidates share >80% of their items, keep only the higher-scored one.
- Take top K candidates (default K = 5).

---

## Image Generation

For each top-K candidate:
- Run the same pipeline as `POST /api/v1/wardrobe/outfits/compose`:
  - Collect `clean_image_url` for each item in the candidate.
  - Call `generate_outfit_image(user_image_url, item_image_urls, items_description)`.
  - Store the result in RustFS, save an `Outfit` row with `source = "shuffle"`.
- Generation is async — can be parallelized across candidates (up to thread pool limit).

---

## Output

```
GET /api/v1/shuffle
```

Returns an ordered list of generated outfit suggestions, each with:
- Full outfit metadata (name, vibe, mood, season, occasion)
- `preview_image_url` — the generated try-on image
- `items[]` — the items in the outfit (for the user to inspect individually)
- `event_context` — which calendar event (if any) triggered this suggestion
- `score` — optional, for debugging/transparency

---

## Endpoint Design

```
GET  /api/v1/shuffle
     ?user_image_url=<url>      required — used for virtual try-on generation
     &limit=5                   how many outfit suggestions to return (max 10)
     &event_lookahead_days=7    how many calendar days to look ahead
```

**Response:** `ShuffleOut[]`

```json
[
  {
    "outfit": { ...OutfitComposeOut },
    "event_context": {
      "event_title": "Team standup",
      "event_date": "2026-05-24",
      "mapped_occasion": "smart-casual"
    },
    "score": 0.87
  }
]
```

---

## Data Dependencies

| Dependency | Status | Notes |
|---|---|---|
| Item embeddings | ✅ exists | Stored in `items.embedding` during upload |
| Outfit embeddings | ✅ exists | Stored in `outfits.embedding` during compose |
| Outfit likes | ✅ exists | `outfit_likes` table |
| Google Calendar | ✅ exists | `google_access_token` on user, `gcal_svc` service |
| Virtual try-on pipeline | ✅ exists | `generate_outfit_image()` in `outfit_agent.py` |
| User image URL | ❌ client must provide | No stored user photo yet — passed per-request |

---

## Future Improvements

- **Weather API**: Replace season-by-date with real-time weather (temperature, rain) for finer filtering.
- **Spotify context**: Use current top genre / energy level to bias vibe matching (infrastructure already in `outfits.spotify_context`).
- **Negative feedback**: If user dismisses a suggestion, push their taste vector away from it.
- **Stored user photo**: Let the user save their photo so `user_image_url` doesn't need to be passed on every request.
- **Outfit reuse guard**: Never suggest an outfit the user wore in the past 7 days.
