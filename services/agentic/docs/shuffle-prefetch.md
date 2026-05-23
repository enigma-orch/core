# Shuffle Prefetch — Background Pre-generation System

## Overview

The shuffle prefetch system pre-generates outfit suggestions with try-on
preview images in the background, so `GET /shuffle` can return fully rendered
results instantly rather than waiting on the wan2.7-image model at request
time (which would add 2–5 minutes of latency per request).

The system has two trigger paths:
- **Hourly cron job** — runs automatically for every eligible user.
- **Manual POST endpoint** — lets a user trigger pre-generation on demand
  (e.g. after uploading their profile photo or new wardrobe items).

---

## Architecture

```
APScheduler (every 60 min)
  └─ scheduled_shuffle_prefetch()           workers/shuffle_prefetch.py
       └─ for each user with avatar_url:
            prefetch_for_user(user, db, base_url)
              ├─ skip if wardrobe unchanged since last batch
              ├─ run candidate ranking (same logic as GET /shuffle)
              ├─ for each candidate:
              │    ├─ pick_background_color(vibe, occasion)
              │    ├─ suggest_song(mood, vibe, spotify_tracks)
              │    ├─ generate_outfit_image(avatar_url, item_urls, description, bg_color)
              │    └─ upload PNG → RustFS → preview_url
              ├─ DELETE previous suggestions for this user
              └─ INSERT new OutfitSuggestion rows (expires_at = now + 24h)

POST /api/v1/shuffle/prefetch
  └─ asyncio.create_task(_run())            fires in background, own DB session
       └─ prefetch_for_user(user, bg_db, base_url)
```

---

## Database — `outfit_suggestions` table

```sql
CREATE TABLE public.outfit_suggestions (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           uuid        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_ids          jsonb       NOT NULL,   -- ["uuid-str", ...]
    preview_image_url text,
    season            text        NOT NULL,
    occasion          text,                   -- null = occasion-neutral
    score             float       NOT NULL,
    vibe              text,
    mood              text,
    background_color  text        NOT NULL DEFAULT '#FAFAFA',
    suggested_song    text,
    expires_at        timestamptz NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_outfit_suggestions_user_expires
    ON outfit_suggestions (user_id, expires_at);
```

### Key design decisions

**`item_ids` as JSONB array of strings** — avoids a join table while keeping
item membership queryable. Resolves to full `Item` objects in the API layer.

**`preview_image_url` is nullable** — if `generate_outfit_image` fails for a
candidate (e.g. DashScope timeout), the suggestion row is still saved without
an image. The item grouping and metadata remain useful; the client displays
the item thumbnails instead of a try-on preview.

**Replace-on-run** — every run deletes all previous suggestions for the user
and inserts a fresh batch. This prevents stale rows from accumulating and
ensures `GET /shuffle` never mixes old and new suggestions.

**24-hour TTL** — `expires_at = now() + 24h`. The GET endpoint filters on
`expires_at > now()`, so suggestions expire naturally without a cleanup job.

---

## Prefetch Worker — `app/workers/shuffle_prefetch.py`

### `prefetch_for_user(user, db, base_url)`

| Step | Detail |
|---|---|
| **1. Load items** | Fetches all `Item` rows for the user. Returns early if none. |
| **2. Staleness check** | Compares `max(items.updated_at)` against `max(outfit_suggestions.created_at)` for this user. Skips if wardrobe unchanged — avoids redundant API calls. |
| **3. Season filter** | Runs `filter_by_season(items, current_season())`. Falls back to all items if no seasonal items exist. |
| **4. Taste vector** | `OutfitRepository.get_taste_vector()` — centroid of liked-outfit embeddings, falls back to worn-outfit embeddings. |
| **5. Candidate ranking** | `build_candidates(items, taste, occasion=None, limit=5)` — same algorithm as GET /shuffle, occasion-neutral. |
| **6. Spotify tracks** | Fetches 20 most-recently-played tracks with audio features (best-effort, skipped if no Spotify linked). |
| **7. Per-candidate generation** | For each candidate: pick bg_color → pick song → call wan2.7-image → upload PNG. Image errors are caught; the suggestion is saved without a preview URL. |
| **8. Persist** | `DELETE` old suggestions → `INSERT` new rows → `flush()`. |

### `scheduled_shuffle_prefetch()`

APScheduler entry point. Opens a single `AsyncSessionLocal` session, iterates
all users with a non-null `avatar_url` sequentially, calls
`prefetch_for_user` for each, then commits.

Users are processed **sequentially** (not concurrently). The outfit agent's
`ThreadPoolExecutor` is capped at `max_workers=2`; processing one user at a
time keeps the queue shallow and avoids DashScope rate-limit errors. If user
count grows significantly, add an `asyncio.Semaphore` here.

---

## Cron Schedule

Registered in `app/main.py` via APScheduler:

```python
scheduler.add_job(scheduled_shuffle_prefetch, "interval", minutes=60, id="shuffle_prefetch")
```

Runs once per hour alongside the Spotify sync (15 min) and outfit scraper
(60 min) jobs.

---

## Manual Trigger — `POST /api/v1/shuffle/prefetch`

Fires `prefetch_for_user` in the background for the authenticated user.
Returns `202 Accepted` immediately.

**Requirements:**
- The user must have `avatar_url` set on their account. The endpoint returns
  `400` if not — there is no point generating suggestions without a base photo.
- Items must exist in the wardrobe (the worker returns early if none are found,
  which is not an error from the endpoint's perspective).

**Background task isolation:** the task opens its own `AsyncSessionLocal`
session and re-fetches the user object (`bg_db.get(User, user_uuid)`),
independent of the request session that closes when the `202` is returned.

**Typical timeline:** 2–5 minutes for a wardrobe of 10–30 items (5 candidates
× ~30–60s per wan2.7-image call, serialised).

---

## GET /shuffle — Fast Path

Once `outfit_suggestions` rows exist for the user:

```python
pre_rows = await db.scalars(
    select(OutfitSuggestion)
    .where(
        OutfitSuggestion.user_id == user_uuid,
        OutfitSuggestion.expires_at > now,
    )
    .order_by(OutfitSuggestion.score.desc())
    .limit(limit)
)
```

The fast path is **skipped** when `?occasion=` is provided, because
pre-generated suggestions are occasion-neutral. The live fallback then runs
with the specified occasion filter.

---

## Try-on Image Generation

Each preview image is produced by the outfit agent (`app/agents/outfit_agent.py`):

1. Downloads the user's `avatar_url` and each item's `clean_image_url`.
2. Ensures each image meets the 240×240 minimum dimension required by
   wan2.7-image (upscales if needed).
3. Sends all images as base64 to `wan2.7-image` via the DashScope
   `ImageGeneration` API, along with:
   - Structured item descriptions (category, colors, pattern, vibe)
   - The selected `background_color` — injected as instruction 6 in the prompt:
     *"the entire background must be a solid flat {color}. Pure uniform fill."*
4. Returns the result PNG as bytes.
5. The worker uploads to RustFS under `wardrobe/shuffle/{uuid}.png` and stores
   the full URL in `outfit_suggestions.preview_image_url`.

---

## Configuration

| Setting | Default | Description |
|---|---|---|
| `PUBLIC_URL` | `http://localhost:8000` | Base URL prepended to preview image paths by the cron job. Set to your production domain in production. |
| `QWEN_WAN_API_KEY` | — | DashScope API key for wan2.7-image. Required. |
| `QWEN_WAN_MODEL` | `wan2.7-image` | Image generation model. |

---

## Failure Modes

| Failure | Behaviour |
|---|---|
| User has no `avatar_url` | Worker skips the user silently; POST endpoint returns `400`. |
| Wardrobe is empty | Worker returns early; no rows written. |
| Wardrobe unchanged | Worker skips — no redundant API calls. |
| `generate_outfit_image` raises | Warning logged; suggestion saved without `preview_image_url`. |
| DashScope rate limit / timeout | Same as above — partial preview coverage is fine. |
| `upload_file` raises | Warning logged; suggestion saved without `preview_image_url`. |
| Worker crash mid-batch | Previously committed users are unaffected; the failed user retains stale (possibly expired) suggestions until the next run. |
