from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database import AsyncSessionLocal
from app.models.scraped_outfit import ScrapedOutfit
from app.models.user import User
from app.services.weather import Weather, get_weather

logger = logging.getLogger(__name__)

RESULTS_PER_QUERY = 15
MAX_QUERIES = 12
BATCH_TARGET = 20
MIN_IMAGE_DIMENSION = 300
MIN_UPS = 5

GENDER = "men"
WOMENS_TERMS = {"women", "woman", "female", "girl", "her", "she", "miss", "womens", "ladies"}

REDDIT_SUBREDDITS = [
    "streetwear",
    "malefashion",
    "techwearclothing",
    "japanesestreetwear",
]

REDDIT_QUERIES = [
    "casual outfit",
    "youth casual",
    "everyday outfit",
    "streetwear fit",
    "summer casual",
    "minimal fit",
    "daily look",
    "weekend outfit",
]

REDDIT_USER_AGENT = "mac:app.drip:v0.1.0 (by /u/drip)"


DEV_OUTFITS = [
    {
        "image_url": "https://images.unsplash.com/photo-1593030761757-71fae45fa0e7?w=600&q=80",
        "title": "Slim Fit Casual Blazer",
        "brand": "Zara",
        "price": 89.99,
        "source_url": "https://www.zara.com",
        "source_domain": "zara.com",
        "category": "casual",
        "tags": ["casual", "minimalist"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=600&q=80",
        "title": "Casual Streetwear Look",
        "brand": "Urban Outfitters",
        "price": 145.00,
        "source_url": "https://www.urbanoutfitters.com",
        "source_domain": "urbanoutfitters.com",
        "category": "streetwear",
        "tags": ["streetwear", "casual"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?w=600&q=80",
        "title": "Monochrome Smart Suit",
        "brand": "Massimo Dutti",
        "price": 250.00,
        "source_url": "https://www.massimodutti.com",
        "source_domain": "massimodutti.com",
        "category": "formal",
        "tags": ["smart casual", "minimalist"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=600&q=80",
        "title": "Oversized Hoodie & Cargos",
        "brand": "Nike",
        "price": 130.00,
        "source_url": "https://www.nike.com",
        "source_domain": "nike.com",
        "category": "streetwear",
        "tags": ["streetwear", "casual"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80",
        "title": "Trench Coat & White Sneakers",
        "brand": "COS",
        "price": 190.00,
        "source_url": "https://www.cos.com",
        "source_domain": "cos.com",
        "category": "casual",
        "tags": ["minimalist", "smart casual"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=80",
        "title": "Leather Jacket & Ripped Jeans",
        "brand": "AllSaints",
        "price": 350.00,
        "source_url": "https://www.allsaints.com",
        "source_domain": "allsaints.com",
        "category": "casual",
        "tags": ["streetwear", "minimalist"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1495121553079-4c61bcce1894?w=600&q=80",
        "title": "Summer Linen Shirt",
        "brand": "Uniqlo",
        "price": 39.90,
        "source_url": "https://www.uniqlo.com",
        "source_domain": "uniqlo.com",
        "category": "casual",
        "tags": ["casual", "summer"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1542282088-fe8426682b8f?w=600&q=80",
        "title": "Denim Jacket & White Tee",
        "brand": "Levi's",
        "price": 98.00,
        "source_url": "https://www.levis.com",
        "source_domain": "levis.com",
        "category": "casual",
        "tags": ["casual", "classic"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1609505848912-b7c3b8b4beda?w=600&q=80",
        "title": "Black Puffer Jacket & Cargos",
        "brand": "The North Face",
        "price": 175.00,
        "source_url": "https://www.thenorthface.com",
        "source_domain": "thenorthface.com",
        "category": "streetwear",
        "tags": ["streetwear", "winter"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1617127365659-c47d86416bae?w=600&q=80",
        "title": "Graphic Tee & Vintage Jeans",
        "brand": "Supreme",
        "price": 220.00,
        "source_url": "https://www.supreme.com",
        "source_domain": "supreme.com",
        "category": "streetwear",
        "tags": ["streetwear", "casual"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=600&q=80",
        "title": "Tailored Grey Suit",
        "brand": "Hugo Boss",
        "price": 450.00,
        "source_url": "https://www.hugoboss.com",
        "source_domain": "hugoboss.com",
        "category": "formal",
        "tags": ["smart casual", "formal"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&q=80",
        "title": "Wool Overcoat & Scarf",
        "brand": "Burberry",
        "price": 590.00,
        "source_url": "https://www.burberry.com",
        "source_domain": "burberry.com",
        "category": "formal",
        "tags": ["minimalist", "smart casual"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&q=80",
        "title": "Light Bomber Jacket & Chinos",
        "brand": "Ralph Lauren",
        "price": 198.00,
        "source_url": "https://www.ralphlauren.com",
        "source_domain": "ralphlauren.com",
        "category": "casual",
        "tags": ["casual", "classic"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=600&q=80",
        "title": "Relaxed fit Linen Set",
        "brand": "Ami Paris",
        "price": 310.00,
        "source_url": "https://www.amiparis.com",
        "source_domain": "amiparis.com",
        "category": "casual",
        "tags": ["minimalist", "summer"],
    },
    {
        "image_url": "https://images.unsplash.com/photo-1596728325488-58c87691e9af?w=600&q=80",
        "title": "Retro Track Jacket",
        "brand": "Adidas",
        "price": 85.00,
        "source_url": "https://www.adidas.com",
        "source_domain": "adidas.com",
        "category": "streetwear",
        "tags": ["streetwear", "casual"],
    },
]

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


def _current_season() -> str:
    month = datetime.now(timezone.utc).month
    if month in (12, 1, 2):
        return "winter"
    elif month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    return "autumn"


def _parse_price(title: str, snippet: str | None = None) -> float | None:
    combined = f"{title} {snippet or ''}"
    match = re.search(r'\$\s*(\d+(?:\.\d{2})?)', combined)
    if match:
        return float(match.group(1))
    match = re.search(r'(\d+(?:\.\d{2})?)\s*(?:€|£)', combined)
    if match:
        return float(match.group(1))
    return None


def _normalize_url(url: str) -> str | None:
    url = url.strip()
    if url.startswith("http://"):
        url = "https://" + url[7:]
    elif not url.startswith("https://"):
        return None
    return url


def _looks_like_webp(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".webp") or ".webp?" in path or ".webp#" in path


def _looks_like_thumbnail(url: str) -> bool:
    path = urlparse(url).path.lower()
    hostname = urlparse(url).hostname or ""
    parts = path.split("/")
    for p in parts:
        if any(kw in p for kw in ("thumb", "small", "icon", "50x", "100x", "150x", "200x", "236x")):
            return True
    if any(d in hostname for d in ("tse", "thf", "th.bing", "tse1", "tse2", "tse3", "tse4")):
        return True
    try:
        from urllib.parse import parse_qs, urlparse as up
        qs = parse_qs(up(url).query)
        w = qs.get("w")
        h = qs.get("h")
        if w and h:
            w_val = int(w[0])
            h_val = int(h[0])
            if w_val < 300 or h_val < 300:
                return True
    except (ValueError, IndexError):
        pass
    return False


def _extract_brand_from_domain(domain: str) -> str | None:
    domain_clean = domain.replace("www.", "").split(".")[0]
    return domain_clean.capitalize() if domain_clean else None


def _clean_title(raw: str) -> str:
    if not raw:
        return "Outfit"
    title = raw.strip()
    # Remove duplicated "men men" prefix from old queries
    title = re.sub(r'\bmen\s+men\b', 'men', title, flags=re.IGNORECASE)
    return title[:200] if title else "Outfit"


async def _validate_image_url(url: str, client: httpx.AsyncClient) -> bool:
    if not url.startswith("https://"):
        return False
    if _looks_like_webp(url):
        return False
    if _looks_like_thumbnail(url):
        return False
    try:
        resp = await client.head(url, follow_redirects=True, timeout=8)
        if resp.status_code != 200:
            return False
        content_type = (resp.headers.get("content-type") or "").lower()
        if not content_type:
            return True
        if "webp" in content_type:
            return False
        if "image/" in content_type:
            return True
        return True
    except (httpx.TimeoutException, httpx.RequestError):
        return False
    except Exception:
        return False


async def _search_reddit(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search Reddit fashion subreddits for image posts with upvotes."""
    results = []
    seen = set()

    REDDIT_LISTINGS = [
        ("top", {"t": "month", "limit": 50}),
        ("hot", {"limit": 50}),
    ]

    for subreddit in REDDIT_SUBREDDITS:
        for listing, params in REDDIT_LISTINGS:
            if len(results) >= RESULTS_PER_QUERY:
                break
            try:
                url = f"https://www.reddit.com/r/{subreddit}/{listing}.json"
                resp = await client.get(
                    url,
                    params=params,
                    headers={"User-Agent": REDDIT_USER_AGENT},
                    follow_redirects=True,
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue

                data = resp.json()
                posts = data.get("data", {}).get("children", [])
                for post_data in posts:
                    if len(results) >= RESULTS_PER_QUERY:
                        break
                    post = post_data.get("data", {})
                    url = post.get("url", "")
                    domain = post.get("domain", "")
                    ups = post.get("ups", 0)
                    title = post.get("title", "") or query

                    if ups < MIN_UPS:
                        continue

                    if not _is_men_fashion(title, None):
                        continue

                    image_url = _normalize_url(url)
                    if not image_url:
                        continue

                    if image_url in seen:
                        continue
                    seen.add(image_url)

                    # Only accept direct image URLs
                    is_direct_img = any(image_url.endswith(ext) for ext in (".jpg", ".jpeg", ".png"))
                    is_reddit_direct = domain == "i.redd.it"
                    is_imgur_direct = domain == "i.imgur.com"

                    if not (is_direct_img or is_reddit_direct or is_imgur_direct):
                        # Try converting imgur.com/xxx to i.imgur.com/xxx.jpg
                        if "imgur.com" in domain and domain != "i.imgur.com":
                            imgur_id = url.rstrip("/").split("/")[-1].split("?")[0]
                            if imgur_id and not any(bad in url for bad in ("/a/", "/gallery", "/user/")):
                                image_url = f"https://i.imgur.com/{imgur_id}.jpg"
                                if image_url in seen:
                                    continue
                                seen.add(image_url)
                            else:
                                continue
                        else:
                            continue

                    results.append({
                        "image": image_url,
                        "title": _clean_title(title),
                        "ups": ups,
                        "subreddit": subreddit,
                        "source": "reddit",
                        "source_url": f"https://www.reddit.com{post.get('permalink', '')}",
                    })

                logger.info("Reddit r/%s %s: %d posts", subreddit, listing, len(posts))

            except Exception as exc:
                logger.warning("Reddit r/%s %s failed: %s", subreddit, listing, exc)

    return results[:RESULTS_PER_QUERY]


def _extract_google_image_urls(text: str, query: str) -> list[dict]:
    """Extract image URLs from Google Images search page HTML."""
    results = []
    seen = set()

    # Strategy 1: extract from script JSON blocks with image URLs
    for script_match in re.finditer(
        r'<script[^>]*>[^<]*?AF_initDataCallback[^}]*?data:\s*(\[.*?\])\s*[}\]][^}]*?</script>',
        text,
        re.DOTALL,
    ):
        try:
            data = json.loads(script_match.group(1))
            _walk_google_data(data, results, seen)
        except (json.JSONDecodeError, TypeError, IndexError):
            pass

    # Strategy 2: extract img src/data-src with any image-like extension
    for attr in ("src", "data-src"):
        for img_match in re.finditer(
            rf'{attr}="(https?://[^"]+)"',
            text,
        ):
            url = img_match.group(1)
            if url in seen:
                continue
            path = urlparse(url).path.lower()
            if not any(ext in path for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
                continue
            seen.add(url)
            results.append({"image": url, "title": query})

    # Strategy 3: Google serves result images via their own domain
    # e.g. https://encrypted-tbn0.gstatic.com/images?q=tbn:...
    for img_match in re.finditer(
        r'src="(https?://encrypted-tbn\d\.gstatic\.com[^"]+)"',
        text,
    ):
        url = img_match.group(1)
        if url not in seen:
            seen.add(url)
            results.append({"image": url, "title": query})

    return results


def _walk_google_data(data, results: list, seen: set) -> None:
    """Recursively walk parsed JSON data from Google looking for image URLs."""
    if isinstance(data, list):
        for item in data:
            _walk_google_data(item, results, seen)
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(key, str) and key.startswith("http") and key not in seen:
                if any(ext in key.lower() for ext in (".jpg", ".jpeg", ".png")):
                    seen.add(key)
                    results.append({"image": key, "title": "Outfit"})
            _walk_google_data(value, results, seen)


async def _search_google_images(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Scrape Google Images search results — no API key required."""
    try:
        resp = await client.get(
            "https://www.google.com/search",
            params={"q": query, "tbm": "isch", "hl": "en"},
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=15,
        )
        resp.raise_for_status()
        results = _extract_google_image_urls(resp.text, query)

        logger.info("Google Images found %d results for '%s'", len(results), query)
        return results[:RESULTS_PER_QUERY]

    except Exception as exc:
        logger.warning("Google Images search failed for '%s': %s", query, exc)
        return []


async def _search_bing_images(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Scrape Bing Images search results — no API key required."""
    try:
        resp = await client.get(
            "https://www.bing.com/images/search",
            params={"q": query, "form": "HDRSC2"},
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=15,
        )
        resp.raise_for_status()
        text = resp.text
        results = []

        seen = set()
        # Extract any image src from img tags that isn't a Bing SVG/logo
        for img_match in re.finditer(
            r'<img[^>]*src="(https?://[^"]+)"[^>]*>',
            text,
        ):
            url = img_match.group(1)
            if url in seen:
                continue
            host = urlparse(url).hostname or ""
            # Skip Bing SVG icons, logos, and tracking pixels
            if host in ("r.bing.com", "c.bing.com", "thf.bing.com"):
                continue
            path = urlparse(url).path.lower()
            if path.endswith(".svg"):
                continue
            seen.add(url)
            alt_match = re.search(r'alt="([^"]*)"', img_match.group(0))
            title = alt_match.group(1) if alt_match else query
            results.append({"image": url, "title": title})

        # Also check data-src on any element
        for dsrc in re.finditer(
            r'data-src="(https?://[^"]+)"', text,
        ):
            url = dsrc.group(1)
            if url in seen:
                continue
            host = urlparse(url).hostname or ""
            if host in ("r.bing.com", "c.bing.com", "thf.bing.com"):
                continue
            if "bing" in host:
                continue
            seen.add(url)
            results.append({"image": url, "title": query})

        logger.info("Bing Images found %d results for '%s'", len(results), query)
        return results[:RESULTS_PER_QUERY]

    except Exception as exc:
        logger.warning("Bing Images search failed for '%s': %s", query, exc)
        return []


async def _search_google_cse(query: str, client: httpx.AsyncClient, start: int = 1) -> list[dict]:
    if not settings.google_api_key or not settings.google_cse_id:
        return []
    try:
        resp = await client.get(
            SEARCH_URL,
            params={
                "key": settings.google_api_key,
                "cx": settings.google_cse_id,
                "q": query,
                "num": 10,
                "searchType": "image",
                "start": start,
                "imgSize": "xlarge",
                "imgType": "photo",
                "safe": "active",
            },
            timeout=12,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception as exc:
        logger.warning("Google CSE failed for '%s': %s", query, exc)
        return []


def _is_men_fashion(title: str, snippet: str | None) -> bool:
    combined = f"{title} {snippet or ''}".lower()
    has_womens = any(term in combined for term in WOMENS_TERMS)
    has_mens = GENDER in combined
    if has_womens and not has_mens:
        return False
    fashion_terms = {"outfit", "wear", "fashion", "style", "look", "clothing",
                     "shop", "collection", "apparel", "streetwear", "ootd",
                     "trend", "casual", "urban", "denim", "jacket", "hoodie",
                     "wdywt", "wdyt", "fit", "uniform"}
    return any(term in combined for term in fashion_terms)


async def _search_all_sources(query: str, client: httpx.AsyncClient) -> list[dict]:
    for source_name, source_fn in [
        ("Reddit", _search_reddit),
        ("Google Images", _search_google_images),
        ("Bing Images", _search_bing_images),
        ("Google CSE", _search_google_cse),
    ]:
        items = await source_fn(query, client)
        if items:
            logger.info("%s returned %d results for '%s'", source_name, len(items), query)
            return items
        logger.info("%s returned 0 results for '%s'", source_name, query)
    return []


async def scrape_outfits_for_user(user: User, session: AsyncSession, weather: Weather | None = None) -> int:
    if not weather:
        weather = await get_weather(user.location)

    styles = user.preferred_styles or ["casual"]
    existing = await session.scalars(
        select(ScrapedOutfit.image_url).where(ScrapedOutfit.user_id == user.id)
    )
    existing_urls = set(existing.all())

    queries = REDDIT_QUERIES[:MAX_QUERIES]
    total_added = 0
    c = 0  # counter for alternating items

    async with httpx.AsyncClient(timeout=15) as client:
        for query in queries:
            if total_added >= BATCH_TARGET:
                break

            items = await _search_all_sources(query, client)
            if not items:
                continue

            for item in items:
                if total_added >= BATCH_TARGET:
                    break

                image_url = _normalize_url(item.get("image", "") or item.get("link", ""))
                if not image_url:
                    continue

                if image_url in existing_urls:
                    continue

                title = _clean_title(item.get("title", "") or query)
                snippet = item.get("snippet", "") or ""

                if not _is_men_fashion(title, snippet):
                    continue

                if not await _validate_image_url(image_url, client):
                    continue

                style = styles[c % len(styles)]
                c += 1

                brand = item.get("brand") or None
                if not brand and "source_domain" in item:
                    brand = _extract_brand_from_domain(item["source_domain"])
                price = item.get("price") or _parse_price(title)
                ups = item.get("ups")
                subreddit = item.get("subreddit")
                source_url = item.get("source_url", "")

                meta_data = {
                    "query": query,
                    "source": item.get("source", "scrape"),
                    "season": _current_season(),
                }
                if ups is not None:
                    meta_data["ups"] = ups
                if subreddit:
                    meta_data["subreddit"] = subreddit

                outfit = ScrapedOutfit(
                    user_id=user.id,
                    image_url=image_url,
                    title=title,
                    brand=brand,
                    price=price,
                    source_url=source_url or snippet,
                    source_domain=None,
                    category=style.lower(),
                    tags=[style],
                    style_tags=[style],
                    weather_tags=weather.tags,
                    meta_data=meta_data,
                )
                session.add(outfit)
                existing_urls.add(image_url)
                total_added += 1

    if total_added == 0:
        logger.info("No outfits found from web scraping, falling back to dev outfits")
        for data in DEV_OUTFITS:
            if total_added >= BATCH_TARGET:
                break
            if data["image_url"] in existing_urls:
                continue
            outfit = ScrapedOutfit(
                user_id=user.id,
                image_url=data["image_url"],
                title=data["title"],
                brand=data["brand"],
                price=data["price"],
                source_url=data["source_url"],
                source_domain=data["source_domain"],
                category=data["category"],
                tags=data["tags"],
                style_tags=data["tags"],
                weather_tags=weather.tags,
            )
            session.add(outfit)
            existing_urls.add(data["image_url"])
            total_added += 1

    logger.info("Scraped %d outfits for user %s", total_added, user.id)
    return total_added


async def scrape_all_users() -> None:
    async with AsyncSessionLocal() as session:
        users = (await session.scalars(
            select(User).where(User.preferred_styles.is_not(None))
        )).all()
        if not users:
            logger.info("No users with style preferences found — skipping scrape")
            return
        for user in users:
            weather = await get_weather(user.location)
            await scrape_outfits_for_user(user, session, weather)
        await session.commit()
