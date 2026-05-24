"""Config-driven multi-retailer scraper engine.



All scrapers return dicts shaped like ScrapedOutfit so they slot straight into
the existing persistence layer without changes.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.services.weather import Weather

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
_JSON_HEADERS = {**_HEADERS, "Accept": "application/json, text/plain, */*"}

_SEMAPHORE = asyncio.Semaphore(4)  # max 4 concurrent store fetches

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CategorySet:
    cold: list[tuple[str, str]]   # [(display_name, url_path)]
    hot:  list[tuple[str, str]]
    mild: list[tuple[str, str]]


@dataclass
class StoreConfig:
    name:     str
    domain:   str
    base_url: str
    strategy: str           # "inditex" | "hm" | "mango" | "uniqlo" | "html"
    men:      CategorySet
    women:    CategorySet | None = None
    # CDN prefix used by some stores to construct full image URLs from paths
    image_cdn: str = ""
    # Extra strategy-specific knobs
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Store catalogue — 40 stores
# ---------------------------------------------------------------------------

STORES: list[StoreConfig] = [

    # ── Inditex Group ────────────────────────────────────────────────────────

    StoreConfig(
        name="Bershka", domain="bershka.com",
        base_url="https://www.bershka.com", strategy="inditex",
        men=CategorySet(
            cold=[("Coats",   "/en/man-coats-c1010251003.html"),
                  ("Jackets", "/en/man-jackets-c1010194000.html"),
                  ("Knitwear","/en/man-knitwear-c1010184006.html")],
            hot= [("T-Shirts","/en/man-t-shirts-c1010182013.html"),
                  ("Shirts",  "/en/man-shirts-c1010182014.html"),
                  ("Shorts",  "/en/man-shorts-c1010185015.html")],
            mild=[("Shirts",  "/en/man-shirts-c1010182014.html"),
                  ("Trousers","/en/man-trousers-c1010185019.html"),
                  ("Jackets", "/en/man-jackets-c1010194000.html")],
        ),
    ),

    StoreConfig(
        name="Pull&Bear", domain="pullandbear.com",
        base_url="https://www.pullandbear.com", strategy="inditex",
        men=CategorySet(
            cold=[("Coats",   "/en/man-coats-l723.html"),
                  ("Jackets", "/en/man-jackets-l637.html"),
                  ("Knit",    "/en/man-knitwear-l679.html")],
            hot= [("T-Shirts","/en/man-t-shirts-l855.html"),
                  ("Shirts",  "/en/man-shirts-l733.html"),
                  ("Shorts",  "/en/man-shorts-l749.html")],
            mild=[("Shirts",  "/en/man-shirts-l733.html"),
                  ("Trousers","/en/man-trousers-l839.html"),
                  ("Jackets", "/en/man-jackets-l637.html")],
        ),
    ),

    StoreConfig(
        name="Massimo Dutti", domain="massimodutti.com",
        base_url="https://www.massimodutti.com", strategy="inditex",
        men=CategorySet(
            cold=[("Coats",   "/en/man-coats-l1143.html"),
                  ("Jackets", "/en/man-jackets-l1064.html"),
                  ("Knit",    "/en/man-knitwear-l1078.html")],
            hot= [("Shirts",  "/en/man-shirts-l1148.html"),
                  ("T-Shirts","/en/man-t-shirts-l1236.html"),
                  ("Trousers","/en/man-trousers-l1176.html")],
            mild=[("Shirts",  "/en/man-shirts-l1148.html"),
                  ("Trousers","/en/man-trousers-l1176.html"),
                  ("Jackets", "/en/man-jackets-l1064.html")],
        ),
    ),

    StoreConfig(
        name="Stradivarius", domain="stradivarius.com",
        base_url="https://www.stradivarius.com", strategy="inditex",
        men=CategorySet(
            cold=[("Coats",   "/en/man-coats-l1204.html"),
                  ("Jackets", "/en/man-jackets-l1115.html"),
                  ("Knit",    "/en/man-knitwear-l1153.html")],
            hot= [("T-Shirts","/en/man-t-shirts-l1363.html"),
                  ("Shirts",  "/en/man-shirts-l1218.html"),
                  ("Shorts",  "/en/man-shorts-l1356.html")],
            mild=[("Shirts",  "/en/man-shirts-l1218.html"),
                  ("Trousers","/en/man-trousers-l1336.html"),
                  ("Jackets", "/en/man-jackets-l1115.html")],
        ),
    ),

    StoreConfig(
        name="Oysho", domain="oysho.com",
        base_url="https://www.oysho.com", strategy="inditex",
        # Oysho is primarily women's — proxy through women categories
        men=CategorySet(
            cold=[("Knitwear", "/en/woman-knitwear-l1152.html"),
                  ("Jackets",  "/en/woman-jackets-l1114.html")],
            hot= [("T-Shirts", "/en/woman-t-shirts-l1362.html"),
                  ("Shorts",   "/en/woman-shorts-l1355.html")],
            mild=[("Shirts",   "/en/woman-shirts-l1217.html"),
                  ("Trousers", "/en/woman-trousers-l1335.html")],
        ),
    ),

    StoreConfig(
        name="Lefties", domain="lefties.com",
        base_url="https://www.lefties.com", strategy="inditex",
        men=CategorySet(
            cold=[("Jackets",  "/en/man-jackets-l640.html"),
                  ("Knitwear", "/en/man-knitwear-l681.html")],
            hot= [("T-Shirts", "/en/man-t-shirts-l855.html"),
                  ("Shirts",   "/en/man-shirts-l737.html")],
            mild=[("Shirts",   "/en/man-shirts-l737.html"),
                  ("Trousers", "/en/man-trousers-l838.html")],
        ),
    ),

    # ── H&M Group ────────────────────────────────────────────────────────────

    StoreConfig(
        name="H&M", domain="hm.com",
        base_url="https://www2.hm.com", strategy="hm",
        men=CategorySet(
            cold=[("Jackets & Coats", "/en_us/men/products/jackets-and-coats"),
                  ("Hoodies",         "/en_us/men/products/hoodies-and-sweatshirts"),
                  ("Knitwear",        "/en_us/men/products/knitwear")],
            hot= [("T-Shirts",        "/en_us/men/products/t-shirts-and-tank-tops"),
                  ("Shirts",          "/en_us/men/products/shirts"),
                  ("Shorts",          "/en_us/men/products/shorts")],
            mild=[("Shirts",          "/en_us/men/products/shirts"),
                  ("Trousers",        "/en_us/men/products/trousers"),
                  ("Jackets",         "/en_us/men/products/jackets-and-coats")],
        ),
    ),

    StoreConfig(
        name="COS", domain="cos.com",
        base_url="https://www.cos.com", strategy="hm",
        men=CategorySet(
            cold=[("Coats",    "/en_gbp/men/jackets-and-coats"),
                  ("Knitwear", "/en_gbp/men/knitwear")],
            hot= [("T-Shirts", "/en_gbp/men/t-shirts"),
                  ("Shirts",   "/en_gbp/men/shirts")],
            mild=[("Shirts",   "/en_gbp/men/shirts"),
                  ("Trousers", "/en_gbp/men/trousers")],
        ),
        extra={"hm_variant": "cos"},
    ),

    StoreConfig(
        name="ARKET", domain="arket.com",
        base_url="https://www.arket.com", strategy="hm",
        men=CategorySet(
            cold=[("Coats",   "/en_gbp/men/coats"),
                  ("Jackets", "/en_gbp/men/jackets")],
            hot= [("T-Shirts","/en_gbp/men/t-shirts"),
                  ("Shirts",  "/en_gbp/men/shirts")],
            mild=[("Shirts",  "/en_gbp/men/shirts"),
                  ("Trousers","/en_gbp/men/trousers")],
        ),
        extra={"hm_variant": "arket"},
    ),

    StoreConfig(
        name="Monki", domain="monki.com",
        base_url="https://www.monki.com", strategy="hm",
        men=CategorySet(
            cold=[("Jackets", "/en_gbp/clothing/jackets")],
            hot= [("T-Shirts","/en_gbp/clothing/tops")],
            mild=[("Shirts",  "/en_gbp/clothing/shirts")],
        ),
        extra={"hm_variant": "monki"},
    ),

    StoreConfig(
        name="Weekday", domain="weekday.com",
        base_url="https://www.weekday.com", strategy="hm",
        men=CategorySet(
            cold=[("Jackets", "/en_gbp/men/jackets-and-coats")],
            hot= [("T-Shirts","/en_gbp/men/t-shirts")],
            mild=[("Shirts",  "/en_gbp/men/shirts")],
        ),
        extra={"hm_variant": "weekday"},
    ),

    StoreConfig(
        name="& Other Stories", domain="stories.com",
        base_url="https://www.stories.com", strategy="hm",
        men=CategorySet(
            cold=[("Jackets", "/en_gbp/clothing/jackets")],
            hot= [("Tops",    "/en_gbp/clothing/tops")],
            mild=[("Shirts",  "/en_gbp/clothing/shirts")],
        ),
        extra={"hm_variant": "stories"},
    ),

    # ── Mango ────────────────────────────────────────────────────────────────

    StoreConfig(
        name="Mango", domain="mango.com",
        base_url="https://shop.mango.com", strategy="mango",
        men=CategorySet(
            cold=[("Coats",   "man/outerwear"),
                  ("Jackets", "man/jackets")],
            hot= [("T-Shirts","man/t-shirts"),
                  ("Shirts",  "man/shirts")],
            mild=[("Shirts",  "man/shirts"),
                  ("Trousers","man/trousers")],
        ),
    ),

    # ── Uniqlo ───────────────────────────────────────────────────────────────

    StoreConfig(
        name="Uniqlo", domain="uniqlo.com",
        base_url="https://www.uniqlo.com", strategy="uniqlo",
        men=CategorySet(
            cold=[("Outerwear", "/us/en/c/men-outerwear"),
                  ("Fleece",    "/us/en/c/men-fleece"),
                  ("Sweaters",  "/us/en/c/men-sweaters")],
            hot= [("T-Shirts",  "/us/en/c/men-t-shirts"),
                  ("Shirts",    "/us/en/c/men-casual-shirts"),
                  ("Shorts",    "/us/en/c/men-shorts")],
            mild=[("Shirts",    "/us/en/c/men-casual-shirts"),
                  ("Pants",     "/us/en/c/men-pants"),
                  ("Outerwear", "/us/en/c/men-outerwear")],
        ),
    ),

    # ── HTML-scraped stores ───────────────────────────────────────────────────

    StoreConfig(
        name="ASOS", domain="asos.com",
        base_url="https://www.asos.com", strategy="html",
        men=CategorySet(
            cold=[("Coats",   "/men/jackets-coats/cat/?cid=4209"),
                  ("Hoodies", "/men/hoodies-sweatshirts/cat/?cid=4205")],
            hot= [("T-Shirts","/men/t-shirts-vests/cat/?cid=4169"),
                  ("Shirts",  "/men/shirts/cat/?cid=2626")],
            mild=[("Shirts",  "/men/shirts/cat/?cid=2626"),
                  ("Trousers","/men/trousers/cat/?cid=4583")],
        ),
        extra={"img_selector": r'<img[^>]+src="(https://[^"]+asos-media\.com[^"]+\.jpg[^"]*)"'},
    ),

    StoreConfig(
        name="Nike", domain="nike.com",
        base_url="https://www.nike.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/w/mens-jackets-vests-6yh4lznik1"),
                  ("Hoodies",  "/w/mens-hoodies-sweatshirts-6rivnznik1")],
            hot= [("T-Shirts", "/w/mens-t-shirts-polos-7askoznik1"),
                  ("Shorts",   "/w/mens-shorts-38fphznik1")],
            mild=[("T-Shirts", "/w/mens-t-shirts-polos-7askoznik1"),
                  ("Trousers", "/w/mens-pants-6cogaznik1")],
        ),
        extra={"img_selector": r'"src":"(https://static\.nike\.com/a/images[^"]+\.(jpg|jpeg|png))'},
    ),

    StoreConfig(
        name="Adidas", domain="adidas.com",
        base_url="https://www.adidas.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/us/men-jackets"),
                  ("Hoodies",  "/us/men-hoodies")],
            hot= [("T-Shirts", "/us/men-t-shirts"),
                  ("Shorts",   "/us/men-shorts")],
            mild=[("T-Shirts", "/us/men-t-shirts"),
                  ("Pants",    "/us/men-pants")],
        ),
        extra={"img_selector": r'"image":"(https://assets\.adidas\.com[^"]+\.(jpg|jpeg|png))"'},
    ),

    StoreConfig(
        name="Urban Outfitters", domain="urbanoutfitters.com",
        base_url="https://www.urbanoutfitters.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/mens-jackets-coats"),
                  ("Hoodies",  "/mens-hoodies-sweatshirts")],
            hot= [("T-Shirts", "/mens-graphic-tees"),
                  ("Shorts",   "/mens-shorts")],
            mild=[("Shirts",   "/mens-shirts-button-down"),
                  ("Pants",    "/mens-pants")],
        ),
    ),

    StoreConfig(
        name="Gap", domain="gap.com",
        base_url="https://www.gap.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/browse/men/jackets-and-coats?cid=2088"),
                  ("Sweaters", "/browse/men/sweaters?cid=2091")],
            hot= [("T-Shirts", "/browse/men/t-shirts?cid=2086"),
                  ("Shorts",   "/browse/men/shorts?cid=2089")],
            mild=[("Shirts",   "/browse/men/shirts?cid=2087"),
                  ("Pants",    "/browse/men/pants?cid=2090")],
        ),
    ),

    StoreConfig(
        name="Old Navy", domain="oldnavy.com",
        base_url="https://oldnavy.gap.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/browse/men/jackets-and-coats?cid=2088"),
                  ("Sweaters", "/browse/men/sweaters?cid=2091")],
            hot= [("T-Shirts", "/browse/men/t-shirts?cid=2086"),
                  ("Shorts",   "/browse/men/shorts?cid=2089")],
            mild=[("Shirts",   "/browse/men/shirts?cid=2087"),
                  ("Pants",    "/browse/men/pants?cid=2090")],
        ),
    ),

    StoreConfig(
        name="Banana Republic", domain="bananarepublic.com",
        base_url="https://bananarepublic.gap.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/browse/men/jackets-and-coats?cid=2088"),
                  ("Sweaters", "/browse/men/sweaters?cid=2091")],
            hot= [("T-Shirts", "/browse/men/t-shirts?cid=2086"),
                  ("Shirts",   "/browse/men/shirts?cid=2087")],
            mild=[("Shirts",   "/browse/men/shirts?cid=2087"),
                  ("Pants",    "/browse/men/pants?cid=2090")],
        ),
    ),

    StoreConfig(
        name="Abercrombie & Fitch", domain="abercrombie.com",
        base_url="https://www.abercrombie.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/shop/us/mens-jackets-coats"),
                  ("Hoodies",  "/shop/us/mens-hoodies-sweatshirts")],
            hot= [("T-Shirts", "/shop/us/mens-graphic-tees"),
                  ("Shorts",   "/shop/us/mens-shorts")],
            mild=[("Shirts",   "/shop/us/mens-shirts"),
                  ("Pants",    "/shop/us/mens-pants")],
        ),
    ),

    StoreConfig(
        name="Hollister", domain="hollisterco.com",
        base_url="https://www.hollisterco.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/shop/us/guys-jackets-coats"),
                  ("Hoodies",  "/shop/us/guys-hoodies-sweatshirts")],
            hot= [("T-Shirts", "/shop/us/guys-graphic-tees"),
                  ("Shorts",   "/shop/us/guys-shorts")],
            mild=[("Shirts",   "/shop/us/guys-shirts"),
                  ("Pants",    "/shop/us/guys-pants")],
        ),
    ),

    StoreConfig(
        name="American Eagle", domain="ae.com",
        base_url="https://www.ae.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/c/men/outerwear?catid=cat6580022"),
                  ("Hoodies",  "/c/men/hoodies-and-sweatshirts?catid=cat7490030")],
            hot= [("T-Shirts", "/c/men/t-shirts?catid=cat6580020"),
                  ("Shorts",   "/c/men/shorts?catid=cat6580021")],
            mild=[("Shirts",   "/c/men/shirts?catid=cat6580019"),
                  ("Pants",    "/c/men/pants?catid=cat7290017")],
        ),
    ),

    StoreConfig(
        name="River Island", domain="riverisland.com",
        base_url="https://www.riverisland.com", strategy="html",
        men=CategorySet(
            cold=[("Coats",    "/c/men/coats-and-jackets"),
                  ("Knitwear", "/c/men/knitwear")],
            hot= [("T-Shirts", "/c/men/t-shirts"),
                  ("Shirts",   "/c/men/shirts")],
            mild=[("Shirts",   "/c/men/shirts"),
                  ("Trousers", "/c/men/trousers-and-chinos")],
        ),
    ),

    StoreConfig(
        name="Next", domain="next.co.uk",
        base_url="https://www.next.co.uk", strategy="html",
        men=CategorySet(
            cold=[("Coats",    "/cat/brand-next/department-menswear/category-coats-and-jackets"),
                  ("Knitwear", "/cat/brand-next/department-menswear/category-knitwear")],
            hot= [("T-Shirts", "/cat/brand-next/department-menswear/category-t-shirts"),
                  ("Shirts",   "/cat/brand-next/department-menswear/category-shirts")],
            mild=[("Shirts",   "/cat/brand-next/department-menswear/category-shirts"),
                  ("Trousers", "/cat/brand-next/department-menswear/category-trousers")],
        ),
    ),

    StoreConfig(
        name="Superdry", domain="superdry.com",
        base_url="https://www.superdry.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/mens/jackets"),
                  ("Hoodies",  "/mens/hoodies-sweatshirts")],
            hot= [("T-Shirts", "/mens/t-shirts"),
                  ("Shorts",   "/mens/shorts")],
            mild=[("Shirts",   "/mens/shirts"),
                  ("Trousers", "/mens/trousers-chinos")],
        ),
    ),

    StoreConfig(
        name="New Look", domain="newlook.com",
        base_url="https://www.newlook.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/men/coats-jackets/"),
                  ("Knitwear", "/men/jumpers-knitwear/")],
            hot= [("T-Shirts", "/men/t-shirts/"),
                  ("Shorts",   "/men/shorts/")],
            mild=[("Shirts",   "/men/shirts/"),
                  ("Trousers", "/men/trousers-chinos/")],
        ),
    ),

    StoreConfig(
        name="Jack & Jones", domain="jackjones.com",
        base_url="https://www.jackjones.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/en/men/jackets"),
                  ("Knitwear", "/en/men/knitwear")],
            hot= [("T-Shirts", "/en/men/t-shirts"),
                  ("Shirts",   "/en/men/shirts")],
            mild=[("Shirts",   "/en/men/shirts"),
                  ("Trousers", "/en/men/trousers")],
        ),
    ),

    StoreConfig(
        name="Selected Homme", domain="selected.com",
        base_url="https://www.selected.com", strategy="html",
        men=CategorySet(
            cold=[("Coats",    "/en-gb/men/coats"),
                  ("Jackets",  "/en-gb/men/jackets")],
            hot= [("T-Shirts", "/en-gb/men/t-shirts"),
                  ("Shirts",   "/en-gb/men/shirts")],
            mild=[("Shirts",   "/en-gb/men/shirts"),
                  ("Trousers", "/en-gb/men/trousers")],
        ),
    ),

    StoreConfig(
        name="Puma", domain="puma.com",
        base_url="https://us.puma.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/en/men/clothing/jackets"),
                  ("Hoodies",  "/en/men/clothing/hoodies")],
            hot= [("T-Shirts", "/en/men/clothing/t-shirts"),
                  ("Shorts",   "/en/men/clothing/shorts")],
            mild=[("T-Shirts", "/en/men/clothing/t-shirts"),
                  ("Pants",    "/en/men/clothing/pants")],
        ),
    ),

    StoreConfig(
        name="New Balance", domain="newbalance.com",
        base_url="https://www.newbalance.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/men/clothing/jackets"),
                  ("Hoodies",  "/men/clothing/hoodies-sweatshirts")],
            hot= [("T-Shirts", "/men/clothing/tops-t-shirts"),
                  ("Shorts",   "/men/clothing/shorts")],
            mild=[("T-Shirts", "/men/clothing/tops-t-shirts"),
                  ("Pants",    "/men/clothing/pants")],
        ),
    ),

    StoreConfig(
        name="Forever 21", domain="forever21.com",
        base_url="https://www.forever21.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/mens/jackets-and-coats"),
                  ("Hoodies",  "/mens/hoodies-and-sweatshirts")],
            hot= [("T-Shirts", "/mens/t-shirts"),
                  ("Shorts",   "/mens/shorts")],
            mild=[("Shirts",   "/mens/shirts"),
                  ("Pants",    "/mens/pants-and-trousers")],
        ),
    ),

    StoreConfig(
        name="PacSun", domain="pacsun.com",
        base_url="https://www.pacsun.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/mens/jackets"),
                  ("Hoodies",  "/mens/sweatshirts-hoodies")],
            hot= [("T-Shirts", "/mens/graphic-tees"),
                  ("Shorts",   "/mens/shorts")],
            mild=[("Shirts",   "/mens/shirts"),
                  ("Pants",    "/mens/pants")],
        ),
    ),

    StoreConfig(
        name="Express", domain="express.com",
        base_url="https://www.express.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/mens/coats-jackets"),
                  ("Sweaters", "/mens/sweaters")],
            hot= [("T-Shirts", "/mens/t-shirts"),
                  ("Shorts",   "/mens/shorts")],
            mild=[("Shirts",   "/mens/dress-shirts"),
                  ("Pants",    "/mens/pants")],
        ),
    ),

    StoreConfig(
        name="Zalando", domain="zalando.co.uk",
        base_url="https://www.zalando.co.uk", strategy="html",
        men=CategorySet(
            cold=[("Coats",    "/mens-clothing-coats/"),
                  ("Jackets",  "/mens-clothing-jackets/")],
            hot= [("T-Shirts", "/mens-clothing-t-shirts/"),
                  ("Shorts",   "/mens-clothing-shorts/")],
            mild=[("Shirts",   "/mens-clothing-shirts/"),
                  ("Trousers", "/mens-clothing-trousers/")],
        ),
    ),

    StoreConfig(
        name="Boohoo", domain="boohoo.com",
        base_url="https://www.boohoo.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/mens/jackets-coats"),
                  ("Hoodies",  "/mens/hoodies-sweatshirts")],
            hot= [("T-Shirts", "/mens/t-shirts"),
                  ("Shorts",   "/mens/shorts")],
            mild=[("Shirts",   "/mens/shirts"),
                  ("Trousers", "/mens/trousers")],
        ),
    ),

    StoreConfig(
        name="ASOS Design", domain="asos.com",
        base_url="https://www.asos.com", strategy="html",
        men=CategorySet(
            cold=[("Hoodies",  "/men/hoodies-sweatshirts/cat/?cid=4205")],
            hot= [("Polo",     "/men/polo-shirts/cat/?cid=4172")],
            mild=[("Chinos",   "/men/chinos/cat/?cid=4572")],
        ),
        extra={"img_selector": r'<img[^>]+src="(https://[^"]+asos-media\.com[^"]+\.jpg[^"]*)"'},
    ),

    StoreConfig(
        name="Nasty Gal", domain="nastygal.com",
        base_url="https://www.nastygal.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets", "/tops/jackets-and-coats")],
            hot= [("Tops",    "/tops")],
            mild=[("Tops",    "/tops")],
        ),
    ),

    StoreConfig(
        name="Reserved", domain="reserved.com",
        base_url="https://www.reserved.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/en/man/outerwear/jackets"),
                  ("Knitwear", "/en/man/knitwear")],
            hot= [("T-Shirts", "/en/man/t-shirts"),
                  ("Shirts",   "/en/man/shirts")],
            mild=[("Shirts",   "/en/man/shirts"),
                  ("Trousers", "/en/man/trousers")],
        ),
    ),

    StoreConfig(
        name="Sinsay", domain="sinsay.com",
        base_url="https://www.sinsay.com", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/en/man/outerwear"),
                  ("Knitwear", "/en/man/knitwear")],
            hot= [("T-Shirts", "/en/man/t-shirts"),
                  ("Shorts",   "/en/man/shorts")],
            mild=[("Shirts",   "/en/man/shirts"),
                  ("Trousers", "/en/man/trousers")],
        ),
    ),

    StoreConfig(
        name="New Yorker", domain="newyorker.de",
        base_url="https://www.newyorker.de", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/en/male/clothing/outerwear"),
                  ("Knitwear", "/en/male/clothing/knitwear")],
            hot= [("T-Shirts", "/en/male/clothing/t-shirts"),
                  ("Shorts",   "/en/male/clothing/shorts")],
            mild=[("Shirts",   "/en/male/clothing/shirts"),
                  ("Trousers", "/en/male/clothing/pants")],
        ),
    ),

    StoreConfig(
        name="Springfield", domain="springfield.net",
        base_url="https://www.springfield.net", strategy="html",
        men=CategorySet(
            cold=[("Jackets",  "/en/man/outerwear"),
                  ("Knitwear", "/en/man/knitwear")],
            hot= [("T-Shirts", "/en/man/t-shirts"),
                  ("Shorts",   "/en/man/shorts")],
            mild=[("Shirts",   "/en/man/shirts"),
                  ("Trousers", "/en/man/trousers")],
        ),
    ),
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _weather_bucket(weather: Weather | None) -> str:
    if not weather:
        return "mild"
    if weather.is_cold:
        return "cold"
    if weather.is_hot:
        return "hot"
    return "mild"


def _pick_categories(config: StoreConfig, weather: Weather | None, gender: str) -> list[tuple[str, str]]:
    bucket = _weather_bucket(weather)
    cat_set = config.women if gender == "women" and config.women else config.men
    return getattr(cat_set, bucket, cat_set.mild)


def _extract_price_from_text(text: str) -> float | None:
    match = re.search(r'\$\s*(\d+(?:\.\d{2})?)', text)
    if match:
        return float(match.group(1))
    match = re.search(r'(\d+(?:[.,]\d{2})?)\s*(?:€|£)', text)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


def _make_result(
    image_url: str, title: str, brand: str, domain: str, source_url: str,
    category: str, gender: str, bucket: str, price: float | None = None,
) -> dict:
    return {
        "image_url": image_url,
        "title": title[:200],
        "brand": brand,
        "price": price,
        "source_url": source_url,
        "source_domain": domain,
        "category": category.lower(),
        "tags": [category.lower(), gender, bucket],
        "source_type": "retail",
    }


# ---------------------------------------------------------------------------
# Strategy: Inditex (reuses Zara JSON + image logic for all Inditex stores)
# ---------------------------------------------------------------------------

def _inditex_pick_image(product: dict[str, Any], base_url: str) -> str | None:
    """Extract image URL from Inditex product JSON — handles Zara + other brands."""
    for media_key in ("xmedia", "media"):
        media_list = product.get(media_key) or []
        for media in media_list:
            path = media.get("path") or media.get("url") or ""
            if path.startswith("http"):
                return path
            name = media.get("name") or ""
            ts   = media.get("timestamp") or ""
            if path and name and ts:
                # Infer CDN domain from store base URL
                hostname = base_url.replace("https://www.", "").replace("https://", "")
                cdn_host = hostname.replace(".com", "")
                return f"https://static.{cdn_host}.net/photos//{path}/w/750/{name}.jpg?ts={ts}"
    return None


def _inditex_flatten(payload: Any) -> list[dict]:
    out: list[dict] = []
    if isinstance(payload, dict):
        if "id" in payload and ("xmedia" in payload or "media" in payload or "name" in payload):
            out.append(payload)
        for v in payload.values():
            out.extend(_inditex_flatten(v))
    elif isinstance(payload, list):
        for v in payload:
            out.extend(_inditex_flatten(v))
    return out


def _inditex_price(product: dict[str, Any]) -> float | None:
    price = product.get("price")
    if isinstance(price, (int, float)):
        return round(price / 100.0, 2) if price > 200 else float(price)
    detail = product.get("detail") or {}
    colors = detail.get("colors") or []
    if colors:
        cents = colors[0].get("price")
        if isinstance(cents, (int, float)):
            return round(cents / 100.0, 2)
    return None


async def _scrape_inditex(
    client: httpx.AsyncClient,
    config: StoreConfig,
    weather: Weather | None,
    gender: str,
    limit: int,
) -> list[dict]:
    bucket = _weather_bucket(weather)
    categories = _pick_categories(config, weather, gender)
    seen_ids: set[str] = set()
    results: list[dict] = []

    for cat_name, path in categories:
        if len(results) >= limit:
            break
        url = f"{config.base_url}{path}"
        async with _SEMAPHORE:
            try:
                resp = await client.get(
                    url, params={"ajax": "true"}, headers=_JSON_HEADERS, timeout=15,
                )
            except Exception as exc:
                logger.warning("%s fetch %s failed: %s", config.name, path, exc)
                continue

        payload: Any = None
        ct = resp.headers.get("content-type", "")
        if "json" in ct:
            try:
                payload = resp.json()
            except Exception:
                pass
        if payload is None:
            # Fallback: script-embedded JSON
            for raw in re.findall(
                r'<script[^>]*>\s*window\.__INITIAL_STATE__\s*=\s*({.+?})\s*;\s*</script>',
                resp.text, re.DOTALL,
            ):
                try:
                    payload = json.loads(raw)
                    break
                except Exception:
                    continue
        if not payload:
            continue

        for product in _inditex_flatten(payload):
            if len(results) >= limit:
                break
            pid = str(product.get("id") or "")
            if not pid or pid in seen_ids:
                continue
            image_url = _inditex_pick_image(product, config.base_url)
            if not image_url:
                continue
            name = (product.get("name") or product.get("title") or cat_name).strip()
            seo = product.get("seo") or {}
            keyword = seo.get("keyword") or pid
            source_url = f"{config.base_url}/en/-{keyword}-p{pid}.html"
            results.append(_make_result(
                image_url=image_url,
                title=name,
                brand=config.name,
                domain=config.domain,
                source_url=source_url,
                category=cat_name,
                gender=gender,
                bucket=bucket,
                price=_inditex_price(product),
            ))
            seen_ids.add(pid)

    logger.info("%s (inditex) → %d products", config.name, len(results))
    return results


# ---------------------------------------------------------------------------
# Strategy: H&M Group
# ---------------------------------------------------------------------------

async def _scrape_hm(
    client: httpx.AsyncClient,
    config: StoreConfig,
    weather: Weather | None,
    gender: str,
    limit: int,
) -> list[dict]:
    bucket = _weather_bucket(weather)
    categories = _pick_categories(config, weather, gender)
    results: list[dict] = []
    seen: set[str] = set()

    for cat_name, path in categories:
        if len(results) >= limit:
            break
        # H&M product listing JSON endpoint
        json_url = f"{config.base_url}{path}/_jcr_content/main/productlisting.display.json"
        params = {"ajaxPatterns": "true", "sortBy": "stock", "pageId": "0", "pageSize": "24"}
        async with _SEMAPHORE:
            try:
                resp = await client.get(json_url, params=params, headers=_JSON_HEADERS, timeout=15)
            except Exception as exc:
                logger.warning("%s fetch %s failed: %s", config.name, path, exc)
                continue

        products: list[dict] = []
        if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
            try:
                data = resp.json()
                products = data.get("results") or data.get("products") or []
            except Exception:
                pass

        if not products:
            # Fallback: grab images from plain HTML listing
            try:
                html_resp = await client.get(
                    f"{config.base_url}{path}", headers=_HEADERS, timeout=15,
                )
                imgs = re.findall(
                    r'<img[^>]+(?:src|data-src)="(https://[^"]+image\.hm\.com[^"]+\.jpg[^"]*)"',
                    html_resp.text,
                )
                for img_url in imgs[:limit]:
                    if img_url in seen:
                        continue
                    seen.add(img_url)
                    results.append(_make_result(
                        image_url=img_url, title=cat_name, brand=config.name,
                        domain=config.domain,
                        source_url=f"{config.base_url}{path}",
                        category=cat_name, gender=gender, bucket=bucket,
                    ))
            except Exception:
                pass
            continue

        for item in products:
            if len(results) >= limit:
                break
            imgs = item.get("images") or []
            img_url = imgs[0].get("url") if imgs else None
            if not img_url or img_url in seen:
                continue
            if not img_url.startswith("http"):
                img_url = "https:" + img_url
            seen.add(img_url)
            name = item.get("name") or cat_name
            price_raw = item.get("price", {}) or {}
            price_val = price_raw.get("value") or price_raw.get("current", {}).get("value")
            try:
                price = float(str(price_val).replace(",", "").replace("$", ""))
            except (TypeError, ValueError):
                price = None
            article = item.get("defaultArticle") or {}
            code = article.get("code") or ""
            source_url = f"{config.base_url}{path}/{code}" if code else f"{config.base_url}{path}"
            results.append(_make_result(
                image_url=img_url, title=name, brand=config.name,
                domain=config.domain, source_url=source_url,
                category=cat_name, gender=gender, bucket=bucket, price=price,
            ))

    logger.info("%s (hm) → %d products", config.name, len(results))
    return results


# ---------------------------------------------------------------------------
# Strategy: Mango
# ---------------------------------------------------------------------------

async def _scrape_mango(
    client: httpx.AsyncClient,
    config: StoreConfig,
    weather: Weather | None,
    gender: str,
    limit: int,
) -> list[dict]:
    bucket = _weather_bucket(weather)
    categories = _pick_categories(config, weather, gender)
    results: list[dict] = []
    seen: set[str] = set()

    for cat_name, slug in categories:
        if len(results) >= limit:
            break
        url = f"{config.base_url}/services/productlist/{slug}"
        params = {"country": "US", "language": "en", "sort": "N", "ajax": "true"}
        async with _SEMAPHORE:
            try:
                resp = await client.get(url, params=params, headers=_JSON_HEADERS, timeout=15)
            except Exception as exc:
                logger.warning("%s fetch %s failed: %s", config.name, slug, exc)
                continue

        if resp.status_code != 200:
            continue
        try:
            data = resp.json()
        except Exception:
            continue

        # Mango nests products under groups[].products[]
        groups = data.get("groups") or []
        products_flat: list[dict] = []
        for group in groups:
            products_flat.extend(group.get("products") or [])
        if not products_flat:
            products_flat = data.get("products") or []

        for item in products_flat:
            if len(results) >= limit:
                break
            colors = item.get("colors") or [{}]
            first_color = colors[0] if colors else {}
            images = first_color.get("images") or item.get("images") or []
            img_url = images[0].get("url") or images[0].get("src") if images else None
            if not img_url or img_url in seen:
                continue
            if not img_url.startswith("http"):
                img_url = "https:" + img_url
            seen.add(img_url)
            name = item.get("name") or cat_name
            price = item.get("price") or first_color.get("price")
            if isinstance(price, dict):
                price = price.get("value") or price.get("current")
            try:
                price = float(price) if price is not None else None
            except (TypeError, ValueError):
                price = None
            item_id = item.get("id") or ""
            source_url = f"https://shop.mango.com/us/{slug}/{item_id}"
            results.append(_make_result(
                image_url=img_url, title=name, brand="Mango",
                domain=config.domain, source_url=source_url,
                category=cat_name, gender=gender, bucket=bucket, price=price,
            ))

    logger.info("Mango → %d products", len(results))
    return results


# ---------------------------------------------------------------------------
# Strategy: Uniqlo
# ---------------------------------------------------------------------------

async def _scrape_uniqlo(
    client: httpx.AsyncClient,
    config: StoreConfig,
    weather: Weather | None,
    gender: str,
    limit: int,
) -> list[dict]:
    bucket = _weather_bucket(weather)
    categories = _pick_categories(config, weather, gender)
    results: list[dict] = []
    seen: set[str] = set()

    for cat_name, path in categories:
        if len(results) >= limit:
            break
        # Uniqlo product listing API (US)
        category_code = path.rstrip("/").split("/")[-1]  # e.g. "men-outerwear"
        api_url = (
            f"https://www.uniqlo.com/us/api/commerce/v5/en/products"
            f"?path=%2F{category_code}&offset=0&limit=24&httpFailure=true"
        )
        async with _SEMAPHORE:
            try:
                resp = await client.get(api_url, headers=_JSON_HEADERS, timeout=15)
            except Exception as exc:
                logger.warning("Uniqlo fetch %s failed: %s", path, exc)
                continue

        if resp.status_code != 200:
            continue
        try:
            data = resp.json()
        except Exception:
            continue

        items = (data.get("result") or {}).get("items") or data.get("items") or []
        for item in items:
            if len(results) >= limit:
                break
            images = item.get("images") or {}
            main_img = images.get("main") or {}
            img_url = main_img.get("image") or main_img.get("url")
            if not img_url:
                # Try first chip image
                chips = images.get("chip") or []
                img_url = chips[0].get("image") if chips else None
            if not img_url or img_url in seen:
                continue
            if not img_url.startswith("http"):
                img_url = "https:" + img_url
            seen.add(img_url)
            name = item.get("name") or cat_name
            prices = item.get("prices") or {}
            base_price = prices.get("base") or {}
            price_val = base_price.get("value") or base_price.get("display")
            try:
                price = float(str(price_val).replace("$", "").replace(",", "")) if price_val else None
            except (TypeError, ValueError):
                price = None
            product_id = item.get("productId") or item.get("code") or ""
            source_url = f"https://www.uniqlo.com/us/en/products/{product_id}.html"
            results.append(_make_result(
                image_url=img_url, title=name, brand="Uniqlo",
                domain=config.domain, source_url=source_url,
                category=cat_name, gender=gender, bucket=bucket, price=price,
            ))

    logger.info("Uniqlo → %d products", len(results))
    return results


# ---------------------------------------------------------------------------
# Strategy: Generic HTML scraping
# ---------------------------------------------------------------------------

# Common image URL patterns found in retail store HTML
_GENERIC_IMG_PATTERNS = [
    r'<img[^>]+(?:src|data-src|data-lazy-src)="(https://[^"]+\.(?:jpg|jpeg|png))(?:\?[^"]*)?(?:#[^"]*)?"',
    r'"(?:src|url|image|imageUrl|img_url)"\s*:\s*"(https://[^"]+\.(?:jpg|jpeg|png)(?:\?[^"]*)?)"',
    r"'(https://[^']+\.(?:jpg|jpeg|png)(?:\?[^']*)?)'",
]

_SKIP_DOMAINS = {
    "logo", "icon", "sprite", "pixel", "badge", "rating", "star",
    "brand", "payment", "social", "flag", "arrow", "loading",
}


def _looks_like_product_image(url: str) -> bool:
    lower = url.lower()
    # Skip tiny icons / UI elements
    for bad in _SKIP_DOMAINS:
        if bad in lower:
            return False
    # Must be reasonably large path — skip 1×1 pixel trackers
    if re.search(r'[0-9]x[0-9]', lower):
        return False
    return True


async def _scrape_html(
    client: httpx.AsyncClient,
    config: StoreConfig,
    weather: Weather | None,
    gender: str,
    limit: int,
) -> list[dict]:
    bucket = _weather_bucket(weather)
    categories = _pick_categories(config, weather, gender)
    results: list[dict] = []
    seen: set[str] = set()

    custom_pattern: str | None = config.extra.get("img_selector")

    for cat_name, path in categories:
        if len(results) >= limit:
            break
        url = f"{config.base_url}{path}"
        async with _SEMAPHORE:
            try:
                resp = await client.get(url, headers=_HEADERS, timeout=15, follow_redirects=True)
            except Exception as exc:
                logger.warning("%s fetch %s failed: %s", config.name, path, exc)
                continue

        if resp.status_code != 200:
            continue

        text = resp.text
        img_urls: list[str] = []

        patterns = [custom_pattern] if custom_pattern else _GENERIC_IMG_PATTERNS
        for pattern in patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                img_urls.append(m.group(1))

        # Score images by URL characteristics (prefer product-sized images)
        scored: list[tuple[int, str]] = []
        for img_url in img_urls:
            if img_url in seen:
                continue
            if not img_url.startswith("https://"):
                continue
            if not _looks_like_product_image(img_url):
                continue
            # Prefer URLs that look like product images (contain /product, /p/, article codes…)
            score = 0
            if any(kw in img_url.lower() for kw in ("/product", "/p/", "/item", "/article", "/pdp")):
                score += 2
            if any(kw in img_url.lower() for kw in ("w=", "width=", "/w/", "imwidth")):
                score += 1
            scored.append((score, img_url))

        scored.sort(key=lambda x: -x[0])

        for _, img_url in scored:
            if len(results) >= limit:
                break
            seen.add(img_url)
            # Extract price from surrounding HTML context
            ctx_start = max(0, text.find(img_url) - 300)
            ctx_end   = min(len(text), text.find(img_url) + 300)
            ctx = text[ctx_start:ctx_end]
            price = _extract_price_from_text(ctx)
            # Extract alt text as title fallback
            alt_match = re.search(r'alt="([^"]{4,80})"', ctx)
            title = alt_match.group(1).strip() if alt_match else f"{config.name} {cat_name}"
            results.append(_make_result(
                image_url=img_url, title=title, brand=config.name,
                domain=config.domain, source_url=url,
                category=cat_name, gender=gender, bucket=bucket, price=price,
            ))

    logger.info("%s (html) → %d products", config.name, len(results))
    return results


# ---------------------------------------------------------------------------
# Dispatcher + main entry point
# ---------------------------------------------------------------------------

_STRATEGY_MAP = {
    "inditex": _scrape_inditex,
    "hm":      _scrape_hm,
    "mango":   _scrape_mango,
    "uniqlo":  _scrape_uniqlo,
    "html":    _scrape_html,
}


async def _scrape_store(
    client: httpx.AsyncClient,
    config: StoreConfig,
    weather: Weather | None,
    gender: str,
    limit: int,
) -> list[dict]:
    fn = _STRATEGY_MAP.get(config.strategy)
    if fn is None:
        logger.warning("Unknown strategy %r for %s", config.strategy, config.name)
        return []
    try:
        return await fn(client, config, weather, gender, limit)
    except Exception as exc:
        logger.warning("Store %s scrape error: %s", config.name, exc)
        return []


async def scrape_all_retailers(
    weather: Weather | None = None,
    gender: str = "men",
    limit_per_store: int = 5,
    max_concurrent_stores: int = 8,
) -> list[dict]:
    """Scrape all configured stores and return a combined product list.

    Args:
        weather: Current weather (used to select seasonal categories).
        gender: "men" or "women".
        limit_per_store: Max products to collect from each store.
        max_concurrent_stores: How many stores to hit at the same time.

    Returns:
        Flat list of ScrapedOutfit-shaped dicts from all stores combined.
    """
    # Chunk stores to avoid opening too many connections at once
    all_results: list[dict] = []
    store_chunks = [
        STORES[i:i + max_concurrent_stores]
        for i in range(0, len(STORES), max_concurrent_stores)
    ]

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(20.0),
        headers=_HEADERS,
    ) as client:
        for chunk in store_chunks:
            tasks = [
                _scrape_store(client, cfg, weather, gender, limit_per_store)
                for cfg in chunk
            ]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in chunk_results:
                if isinstance(r, list):
                    all_results.extend(r)
                # Exceptions are swallowed — individual store failures don't break the batch

    logger.info(
        "scrape_all_retailers: %d stores → %d total products",
        len(STORES), len(all_results),
    )
    return all_results
