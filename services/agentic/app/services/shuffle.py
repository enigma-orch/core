"""Shuffle service — suggest outfit combinations from the user's wardrobe.

Pure Python: no LLM, no image generation. The endpoint returns groups of
item IDs ranked by how well they match the user's taste vector and the
requested occasion. The client (or another route) can pipe those IDs into
`/wardrobe/outfits/compose` to render a try-on.

Design choices vs. docs/shuffle.md:
- We always emit suggestions even when the user has no liked outfits —
  in that case we fall back to a centroid of recent items.
- Image generation is intentionally NOT part of /shuffle. Rendering 5
  wan2.7-image calls would make the endpoint >30s; clients decide which
  suggestions to render.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.item import Item

# Combinatorial blow-up guards.
_PER_CATEGORY_CAP = 8
_MAX_CANDIDATES = 20


@dataclass(frozen=True)
class ShuffleCandidate:
    item_ids: tuple[str, ...]
    items: tuple[Item, ...]
    score: float


def current_season(today: datetime | None = None) -> str:
    m = (today or datetime.now(timezone.utc)).month
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    return "fall"


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _item_vector(item: Item) -> list[float]:
    """pgvector returns numpy arrays via SQLAlchemy; coerce to plain list."""
    if item.embedding is None:
        return []
    return list(item.embedding)


def _candidate_embedding(items: tuple[Item, ...]) -> list[float]:
    """Mean of the constituent item embeddings."""
    vectors = [_item_vector(i) for i in items if i.embedding is not None]
    if not vectors:
        return []
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i, x in enumerate(v):
            out[i] += x
    return [x / len(vectors) for x in out]


def filter_by_season(items: list[Item], season: str) -> list[Item]:
    out: list[Item] = []
    for it in items:
        if not it.season:
            # Item not tagged with a season — treat as all-season.
            out.append(it)
            continue
        if season in it.season:
            out.append(it)
    return out


def bucket_by_category(items: list[Item]) -> dict[str, list[Item]]:
    buckets: dict[str, list[Item]] = {}
    for it in items:
        cat = (it.category or "").lower() or "other"
        buckets.setdefault(cat, []).append(it)
    return buckets


def _rank_within_bucket(
    items: list[Item], taste: list[float] | None
) -> list[Item]:
    if taste:
        items = sorted(items, key=lambda it: -_cosine(_item_vector(it), taste))
    else:
        # No taste signal — prefer items the user has worn (proxy for "I like this").
        items = sorted(items, key=lambda it: -it.wear_count)
    return items[:_PER_CATEGORY_CAP]


def _occasion_match(items: tuple[Item, ...], target_occasion: str | None) -> float:
    if not target_occasion:
        return 0.0
    matches = sum(1 for it in items if (it.occasion or "") == target_occasion)
    if matches == 0:
        return 0.0
    return matches / len(items)


def _recency_penalty(items: tuple[Item, ...]) -> float:
    """0..1 — higher means we've worn these items a lot recently."""
    if not items:
        return 0.0
    # Use wear_count clipped to [0, 10] as a crude signal.
    total = sum(min(it.wear_count, 10) for it in items)
    return total / (10 * len(items))


def build_candidates(
    items: list[Item],
    taste: list[float] | None,
    target_occasion: str | None,
    limit: int,
) -> list[ShuffleCandidate]:
    """Assemble top-K outfit candidates.

    Required slots: top + bottom. Optional: shoes, outerwear, accessory.
    A dress fills top+bottom in one item.
    """
    buckets = bucket_by_category(items)
    tops = _rank_within_bucket(buckets.get("top", []), taste)
    bottoms = _rank_within_bucket(buckets.get("bottom", []), taste)
    dresses = _rank_within_bucket(buckets.get("dress", []), taste)
    shoes = _rank_within_bucket(buckets.get("shoes", []), taste)
    outerwear = _rank_within_bucket(buckets.get("outerwear", []), taste)
    accessories = (
        _rank_within_bucket(buckets.get("accessory", []), taste)
        + _rank_within_bucket(buckets.get("bag", []), taste)
        + _rank_within_bucket(buckets.get("jewellery", []), taste)
    )[: _PER_CATEGORY_CAP]

    base_combos: list[tuple[Item, ...]] = []

    # top + bottom combos
    for top, bottom in itertools.islice(itertools.product(tops, bottoms), _MAX_CANDIDATES):
        base_combos.append((top, bottom))
    # dress-only combos count as a full outfit
    for d in dresses[:4]:
        base_combos.append((d,))

    if not base_combos:
        return []

    # Layer in optional pieces — keep it small (one variant per base combo).
    candidates: list[ShuffleCandidate] = []
    for combo in base_combos:
        embellished = combo
        if shoes:
            embellished = embellished + (shoes[0],)
        if outerwear and target_occasion not in {"activewear", "party"}:
            embellished = embellished + (outerwear[0],)
        if accessories:
            embellished = embellished + (accessories[0],)

        cand_emb = _candidate_embedding(embellished)
        sim = _cosine(cand_emb, taste) if taste else 0.0
        occ = _occasion_match(embellished, target_occasion)
        rec = _recency_penalty(embellished)
        score = 0.6 * sim + 0.3 * occ - 0.1 * rec

        candidates.append(
            ShuffleCandidate(
                item_ids=tuple(str(i.id) for i in embellished),
                items=embellished,
                score=score,
            )
        )

    # Dedupe near-duplicates (>= 80% overlap by item id) and rank.
    candidates.sort(key=lambda c: -c.score)
    kept: list[ShuffleCandidate] = []
    for c in candidates:
        is_dup = False
        s_ids = set(c.item_ids)
        for k in kept:
            overlap = len(s_ids & set(k.item_ids)) / max(len(s_ids), 1)
            if overlap >= 0.8:
                is_dup = True
                break
        if not is_dup:
            kept.append(c)
        if len(kept) >= limit:
            break
    return kept


_EVENT_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("interview",), "formal"),
    (("meeting", "office", "work", "presentation", "standup"), "smart-casual"),
    (("wedding", "gala"), "formal"),
    (("party", "birthday", "club", "night out"), "party"),
    (("gym", "workout", "run", "yoga", "pilates", "training"), "activewear"),
    (("date", "dinner"), "smart-casual"),
]


def occasion_from_event_title(title: str | None) -> str | None:
    if not title:
        return None
    lo = title.lower()
    for keywords, occasion in _EVENT_KEYWORDS:
        if any(k in lo for k in keywords):
            return occasion
    return None
