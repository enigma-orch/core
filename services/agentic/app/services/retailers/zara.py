"""Zara product scraper.

Uses Zara's public category JSON endpoint (`/products?ajax=true`) to pull
product cards (image, name, brand, price). No third-party HTML parser
dependency — Zara serves structured JSON. Falls back to script-embedded
JSON extraction if the AJAX endpoint changes shape.

Output dict shape matches `outfit_scraper.DEV_OUTFITS` so it can be persisted
through the same `ScrapedOutfit` model with `source_type='retail'`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.services.weather import Weather

logger = logging.getLogger(__name__)

ZARA_BASE = "https://www.zara.com"

# Public men's category listings (verified product feeds).
# Picking by weather + mood keeps the catalog seasonal.
# Each value is a list of /<locale>/category/<id>/products?ajax=true tails.
MEN_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "cold": [
        ("Coats", "/en/man-coats-l715.html"),
        ("Jackets", "/en/man-jackets-l640.html"),
        ("Knitwear", "/en/man-sweaters-cardigans-l681.html"),
    ],
    "hot": [
        ("T-Shirts", "/en/man-tshirts-l855.html"),
        ("Shirts", "/en/man-shirts-l737.html"),
        ("Shorts", "/en/man-shorts-l747.html"),
    ],
    "mild": [
        ("Shirts", "/en/man-shirts-l737.html"),
        ("Trousers", "/en/man-trousers-l838.html"),
        ("Outerwear", "/en/man-jackets-l640.html"),
    ],
}

WOMEN_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "cold": [
        ("Coats", "/en/woman-coats-l1184.html"),
        ("Jackets", "/en/woman-jackets-l1114.html"),
        ("Knitwear", "/en/woman-knitwear-l1152.html"),
    ],
    "hot": [
        ("Dresses", "/en/woman-dresses-l1066.html"),
        ("T-Shirts", "/en/woman-tshirts-l1362.html"),
        ("Shorts", "/en/woman-shorts-l1355.html"),
    ],
    "mild": [
        ("Shirts", "/en/woman-shirts-l1217.html"),
        ("Trousers", "/en/woman-trousers-l1335.html"),
        ("Outerwear", "/en/woman-jackets-l1114.html"),
    ],
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Concurrency guard — be polite, don't hammer.
_REQUEST_SEMAPHORE = asyncio.Semaphore(2)


def _weather_bucket(weather: Weather | None) -> str:
    if not weather:
        return "mild"
    if weather.is_cold:
        return "cold"
    if weather.is_hot:
        return "hot"
    return "mild"


def _pick_image_url(product: dict[str, Any]) -> str | None:
    """Walk Zara's xmedia array to find the highest-resolution image URL."""
    xmedia = (product.get("xmedia") or product.get("media") or [])
    for media in xmedia:
        path = media.get("path") or media.get("url")
        name = media.get("name") or ""
        timestamp = media.get("timestamp") or ""
        if path and name and timestamp:
            return (
                f"https://static.zara.net/photos//{path}/w/750/{name}.jpg"
                f"?ts={timestamp}"
            )
        if path and path.startswith("http"):
            return path
    return None


def _extract_price(product: dict[str, Any]) -> float | None:
    price = product.get("price")
    if isinstance(price, (int, float)):
        # Zara uses minor units (cents)
        return round(price / 100.0, 2) if price > 200 else float(price)
    detail = product.get("detail") or {}
    colors = detail.get("colors") or []
    if colors:
        first = colors[0]
        cents = first.get("price")
        if isinstance(cents, (int, float)):
            return round(cents / 100.0, 2)
    return None


def _flatten_products(payload: Any) -> list[dict]:
    """Zara nests products under productGroups → elements → commercialComponents."""
    out: list[dict] = []
    if isinstance(payload, dict):
        if "id" in payload and ("xmedia" in payload or "media" in payload or "name" in payload):
            out.append(payload)
        for v in payload.values():
            out.extend(_flatten_products(v))
    elif isinstance(payload, list):
        for v in payload:
            out.extend(_flatten_products(v))
    return out


async def _fetch_category(
    client: httpx.AsyncClient, path: str
) -> list[dict]:
    """Fetch a Zara category listing as JSON."""
    url = f"{ZARA_BASE}{path}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": ZARA_BASE,
    }
    async with _REQUEST_SEMAPHORE:
        try:
            resp = await client.get(url, params={"ajax": "true"}, headers=headers, timeout=15)
            resp.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning("Zara fetch %s failed: %s", path, exc)
            return []

    ct = resp.headers.get("content-type", "")
    if "json" in ct:
        try:
            return _flatten_products(resp.json())
        except json.JSONDecodeError:
            pass

    # Fallback: extract JSON island from HTML
    matches = re.findall(
        r'<script[^>]*>\s*window\.__INITIAL_STATE__\s*=\s*({.+?})\s*;\s*</script>',
        resp.text,
        re.DOTALL,
    )
    for raw in matches:
        try:
            return _flatten_products(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return []


async def scrape_zara(
    weather: Weather | None = None,
    *,
    gender: str = "men",
    limit: int = 20,
) -> list[dict]:
    """Return up to `limit` Zara product cards as ScrapedOutfit-shaped dicts.

    Output dicts contain: image_url, title, brand, price, source_url,
    source_domain, category, tags, source_type='retail'.
    """
    bucket = _weather_bucket(weather)
    catalog = WOMEN_CATEGORIES if gender == "women" else MEN_CATEGORIES
    categories = catalog.get(bucket, catalog["mild"])

    seen_ids: set[str] = set()
    cards: list[dict] = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for category_name, path in categories:
            if len(cards) >= limit:
                break
            products = await _fetch_category(client, path)
            for product in products:
                if len(cards) >= limit:
                    break
                pid = str(product.get("id") or "")
                if not pid or pid in seen_ids:
                    continue
                image_url = _pick_image_url(product)
                if not image_url:
                    continue
                name = (product.get("name") or product.get("title") or category_name).strip()
                if not name:
                    continue
                seo = product.get("seo") or {}
                keyword = seo.get("keyword") or pid
                source_url = f"{ZARA_BASE}/en/-{keyword}-p{pid}.html"

                cards.append({
                    "image_url": image_url,
                    "title": name[:200],
                    "brand": "Zara",
                    "price": _extract_price(product),
                    "source_url": source_url,
                    "source_domain": "zara.com",
                    "category": category_name.lower(),
                    "tags": [category_name.lower(), gender, bucket],
                    "source_type": "retail",
                })
                seen_ids.add(pid)

    logger.info(
        "Zara scrape (gender=%s, bucket=%s) returned %d products", gender, bucket, len(cards)
    )
    return cards
