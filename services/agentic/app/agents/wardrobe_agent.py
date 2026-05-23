"""
Wardrobe detection agent — Qwen (DashScope) only.

Responsibilities:
  - Inspect a clothing image and return a DetectedOutfit (items + outfit metadata).
  - Background removal is NOT handled here; it is a deterministic service call.

The only model used is settings.qwen_model which the config validator
enforces to equal "qwen3.6-flash". Qwen exposes an OpenAI-compatible
API via DashScope, so the openai SDK is used with a custom base_url.
"""

import asyncio
import base64
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
from PIL import Image as PILImage
from pydantic import ValidationError

from app.config import settings
from app.schemas.wardrobe import DetectedClothingItem, DetectedOutfit

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)
_MAX_RETRIES = 2

_ITEM_PROMPT = """\
You are an expert fashion cataloguer. Your output is used directly as input for an AI outfit image generator — precision is critical. Vague or generic descriptions cause hallucinations in the image generator.

This image contains exactly one clothing item. Return ONLY a valid JSON object — no markdown fences, no explanation, no extra text.

─── CATEGORY RULES (pick exactly one) ───
  "top"        → any shirt, tee, tank, blouse, polo, sweatshirt, hoodie, crop top, bodysuit
  "bottom"     → any trousers, jeans, shorts, skirt, joggers, leggings, cargo pants
  "dress"      → any one-piece dress, jumpsuit, romper, playsuit
  "outerwear"  → any jacket, coat, blazer, cardigan, puffer, windbreaker, trench
  "shoes"      → any footwear: sneakers, boots, heels, sandals, loafers, slides
  "bag"        → any bag: backpack, tote, clutch, shoulder bag, crossbody, belt bag
  "accessory"  → hat, cap, scarf, belt, sunglasses, watch, gloves, socks
  "jewellery"  → necklace, bracelet, ring, earrings, anklet

─── NAME RULES ───
  Must be specific enough to reconstruct the item visually. Include: fit + color shade + material (if visible) + type.
  ✓ Good: "Slim-fit washed navy denim jeans"  "Oversized off-white French terry hoodie"  "Tan suede chelsea boots"
  ✗ Bad:  "Jeans"  "Hoodie"  "Boots"

─── COLOR RULES ───
  Be precise. Use compound descriptors.
  ✓ "slate grey"  "dusty rose"  "washed indigo"  "olive green"  "burgundy"
  ✗ "blue"  "red"  "grey"

─── SUBCATEGORY RULES ───
  Be as specific as possible — this feeds the image generator directly.
  ✓ "slim-fit straight-leg chinos"  "low-top leather sneaker"  "mock-neck ribbed knit top"
  ✗ "pants"  "sneaker"  "top"

─── OUTPUT FORMAT ───
{
  "name": "Slim-fit washed navy denim jeans",
  "category": "bottom",
  "subcategory": "slim-fit straight-leg denim jeans",
  "colors": ["washed navy blue"],
  "brand": null,
  "style_tags": ["denim", "minimalist", "slim"],
  "season": ["spring", "fall", "winter"],
  "occasion": "casual | smart-casual | formal | streetwear | activewear | party",
  "pattern": "solid | striped | plaid | floral | geometric | animal | graphic | null",
  "vibe": "clean minimal",
  "mood": "confident",
  "size": "estimated medium",
  "confidence": 0.95,
  "search_query": "slim fit washed navy denim jeans men"
}

STRICT RULES:
- brand → null unless a logo/label is clearly readable in the image.
- pattern → one of: solid, striped, plaid, floral, geometric, animal, graphic — or null if unclear.
- confidence → float 0.0–1.0.
- Do NOT invent details not visible in the image.
- Return ONLY the JSON. Nothing before or after it.
"""


def _detect_sync(image_bytes: bytes) -> DetectedOutfit:
    client = OpenAI(
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
    )

    img = PILImage.open(io.BytesIO(image_bytes))
    fmt = (img.format or "PNG").upper()
    mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(fmt, "image/png")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode()

    last_error: Exception | None = None
    correction_note = ""

    for attempt in range(1 + _MAX_RETRIES):
        prompt = _DETECTION_PROMPT if not correction_note else (
            _DETECTION_PROMPT
            + f"\n\nPrevious attempt failed validation: {correction_note}\n"
            "Fix the JSON and return only the corrected object."
        )
        response = client.chat.completions.create(
            model=settings.qwen_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=4096,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:] if lines[0].startswith("```") else lines)
            raw = raw.rsplit("```", 1)[0].strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            correction_note = f"Invalid JSON: {exc}"
            last_error = exc
            logger.warning("Attempt %d: Qwen returned invalid JSON: %s", attempt + 1, exc)
            continue

        try:
            return DetectedOutfit.model_validate(data)
        except ValidationError as exc:
            correction_note = str(exc)
            last_error = exc
            logger.warning("Attempt %d: Pydantic validation failed: %s", attempt + 1, exc)
            continue

    raise ValueError(
        f"Qwen failed to return valid DetectedOutfit after {1 + _MAX_RETRIES} attempts: {last_error}"
    )


def _detect_item_sync(image_bytes: bytes) -> DetectedClothingItem:
    client = OpenAI(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)

    img = PILImage.open(io.BytesIO(image_bytes))
    fmt = (img.format or "PNG").upper()
    mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(fmt, "image/png")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode()

    last_error: Exception | None = None
    correction_note = ""

    for attempt in range(1 + _MAX_RETRIES):
        prompt = _ITEM_PROMPT if not correction_note else (
            _ITEM_PROMPT
            + f"\n\nPrevious attempt failed validation: {correction_note}\n"
            "Fix the JSON and return only the corrected object."
        )
        response = client.chat.completions.create(
            model=settings.qwen_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=2048,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:] if lines[0].startswith("```") else lines)
            raw = raw.rsplit("```", 1)[0].strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            correction_note = f"Invalid JSON: {exc}"
            last_error = exc
            logger.warning("Attempt %d: Qwen returned invalid JSON: %s", attempt + 1, exc)
            continue

        try:
            return DetectedClothingItem.model_validate(data)
        except ValidationError as exc:
            correction_note = str(exc)
            last_error = exc
            logger.warning("Attempt %d: Pydantic validation failed: %s", attempt + 1, exc)
            continue

    raise ValueError(f"Qwen failed to return valid DetectedClothingItem after {1 + _MAX_RETRIES} attempts: {last_error}")


async def detect_item(image_bytes: bytes) -> DetectedClothingItem:
    """Detect a single clothing item from an image using Qwen qwen3.6-flash."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _detect_item_sync, image_bytes)


async def detect_outfit(image_bytes: bytes) -> DetectedOutfit:
    """Run outfit detection on image_bytes using Qwen qwen3.6-flash."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _detect_sync, image_bytes)
