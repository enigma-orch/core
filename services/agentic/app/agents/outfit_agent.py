"""
Outfit image generation.

Takes the user's photo + item images stored in RustFS and sends them directly
to wan2.7-image via the DashScope ImageGeneration SDK. The model replaces the
user's current outfit with the provided clothing items, producing a
photorealistic virtual try-on result.

No LLM orchestration layer — the call is made directly to the image generation
API to avoid latency and non-determinism from routing through a chat model.
"""

import asyncio
import base64
import logging
from concurrent.futures import ThreadPoolExecutor
import io

import dashscope
import httpx
from PIL import Image
from dashscope.aigc.image_generation import ImageGeneration
from dashscope.api_entities.dashscope_response import Message

from app.config import settings

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)

dashscope.base_http_api_url = settings.qwen_wan_base_http_url

_MIN_DIM = 240  # wan2.7-image minimum dimension per dimension


def _ensure_min_size(img_bytes: bytes, mime: str) -> tuple[bytes, str]:
    """Scale up image if either dimension is below _MIN_DIM."""
    img = Image.open(io.BytesIO(img_bytes))
    w, h = img.size
    if w < _MIN_DIM or h < _MIN_DIM:
        scale = max(_MIN_DIM / w, _MIN_DIM / h)
        new_w, new_h = max(int(w * scale), _MIN_DIM), max(int(h * scale), _MIN_DIM)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        logger.info("Resized image %dx%d → %dx%d", w, h, new_w, new_h)
    buf = io.BytesIO()
    fmt = "PNG" if "png" in mime else "JPEG"
    img.save(buf, format=fmt)
    return buf.getvalue(), f"image/{fmt.lower()}"


def _run_image_generation_sync(
    user_image_url: str,
    item_image_urls: list[str],
    items_description: str,
    background_color: str,
) -> bytes:
    """Blocking DashScope call — runs in a thread via run_in_executor."""
    api_key = settings.qwen_wan_api_key or settings.qwen_api_key

    urls = [user_image_url] + item_image_urls
    content: list[dict] = []

    with httpx.Client(timeout=20) as client:
        for url in urls:
            try:
                resp = client.get(url)
                resp.raise_for_status()
                mime = resp.headers.get("content-type", "image/png").split(";")[0].strip()
                img_bytes, mime = _ensure_min_size(resp.content, mime)
                b64 = base64.b64encode(img_bytes).decode()
                content.append({"image": f"data:{mime};base64,{b64}"})
            except Exception as exc:
                logger.warning("Skipping image %s: %s", url, exc)

    if len(content) < 2:
        raise RuntimeError(
            f"Not enough images could be downloaded (need at least user + 1 item, got {len(content)})"
        )

    content.append({
        "text": (
            "TASK: Virtual fashion try-on.\n\n"
            "IMAGE ORDER:\n"
            "- Image 1: the reference person — their face, body shape, skin tone, and pose must be preserved exactly.\n"
            "- Images 2+: the clothing items to wear, described below.\n\n"
            "ITEM DESCRIPTIONS (ground truth — do NOT deviate from these):\n"
            f"{items_description}\n\n"
            "INSTRUCTIONS:\n"
            "1. Keep the person's face, skin tone, hair, body proportions, and pose identical to Image 1.\n"
            "2. Replace ONLY the clothing.\n"
            "3. Render each item exactly as shown in its reference image AND as described above "
            "(correct color, fit, silhouette, texture, pattern). Do not invent or substitute any item.\n"
            "4. Ensure all items fit naturally on the person's body — correct layering, proportions, and drape.\n"
            "5. Output: photorealistic full-body fashion portrait, soft studio lighting, sharp focus, high resolution.\n"
            f"6. Background: the entire background must be a solid flat {background_color} color. "
            "Pure uniform fill — no gradients, no textures, no patterns, no props, no environment. "
            "Just the person on a clean solid-color background."
        )
    })

    logger.info(
        "wan2.7-image: calling DashScope — user=%s items=%d",
        user_image_url,
        len(item_image_urls),
    )

    rsp = ImageGeneration.call(
        model=settings.qwen_wan_model,
        api_key=api_key,
        messages=[Message(role="user", content=content)],
        enable_sequential=False,
        n=1,
        size="1024*1024",
    )

    if rsp.status_code != 200:
        raise RuntimeError(f"DashScope error {rsp.status_code}: {rsp.message}")

    choices = (rsp.output or {}).get("choices") or []
    if not choices:
        raise RuntimeError(f"No choices in DashScope response: {rsp.output}")

    for block in choices[0].get("message", {}).get("content", []):
        img_val = block.get("image", "")
        if img_val.startswith("data:"):
            _, b64_data = img_val.split(",", 1)
            return base64.b64decode(b64_data)
        if img_val.startswith("http"):
            with httpx.Client(timeout=30) as client:
                img_resp = client.get(img_val)
                img_resp.raise_for_status()
            return img_resp.content

    raise RuntimeError(f"No image found in DashScope response choices: {choices}")


async def generate_outfit_image(
    user_image_url: str,
    item_image_urls: list[str],
    items_description: str,
    background_color: str = "#FAFAFA",
) -> bytes:
    """Dress the user in the given items via wan2.7-image. Returns PNG bytes."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor,
        _run_image_generation_sync,
        user_image_url,
        item_image_urls,
        items_description,
        background_color,
    )
