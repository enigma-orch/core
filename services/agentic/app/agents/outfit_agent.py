"""
Outfit image generation agent.

Takes the user's photo + item images already stored in RustFS (from the upload
pipeline) and sends them directly to wan2.7-image via the DashScope
ImageGeneration SDK.  The model replaces the user's current outfit with the
provided clothing items, producing a photorealistic virtual try-on result.

No re-analysis of items is performed here — all item metadata (vibe, mood,
season, occasion) was already extracted during the upload pipeline and is
read directly from the database by the caller.
"""

import asyncio
import base64
import logging
from concurrent.futures import ThreadPoolExecutor

import io

import dashscope
import httpx
from agno.agent import Agent
from PIL import Image
from agno.models.dashscope import DashScope
from agno.tools import tool
from dashscope.aigc.image_generation import ImageGeneration
from dashscope.api_entities.dashscope_response import Message

from app.config import settings

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)

dashscope.base_http_api_url = settings.qwen_wan_base_http_url

_MIN_DIM = 240  # wan2.7-image minimum dimension

# Out-of-band bytes store — agno tools must return str
_image_result: bytes | None = None


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


@tool
def generate_image(user_image_url: str, item_image_urls: str, items_description: str) -> str:
    """
    Generate a virtual try-on image.

    Sends the user's photo and clothing item images to wan2.7-image.
    The model dresses the user in the provided items using both the visual
    references and the structured item descriptions to avoid hallucination.

    Args:
        user_image_url: URL of the user's photo.
        item_image_urls: Comma-separated URLs of the clothing item images.
        items_description: Structured description of each item from the DB.

    Returns:
        'ok' on success, or an error string on failure.
    """
    global _image_result
    _image_result = None
    logger.info("generate_image tool called: user=%s items=%s", user_image_url, item_image_urls[:80])

    api_key = settings.qwen_wan_api_key or settings.qwen_api_key

    urls = [user_image_url] + [u.strip() for u in item_image_urls.split(",") if u.strip()]

    # DashScope servers cannot reach localhost — download images here and send as base64
    # Also ensure each image meets the 240x240 minimum required by wan2.7-image
    content = []
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
        return "Not enough images could be downloaded (need at least user + 1 item)"

    content.append({
        "text": (
            "TASK: Virtual fashion try-on.\n\n"
            "IMAGE ORDER:\n"
            "- Image 1: the reference person — their face, body shape, skin tone, and pose must be preserved exactly.\n"
            f"- Images 2+: the clothing items to wear, described below.\n\n"
            "ITEM DESCRIPTIONS (ground truth — do NOT deviate from these):\n"
            f"{items_description}\n\n"
            "INSTRUCTIONS:\n"
            "1. Keep the person's face, skin tone, hair, body proportions, and pose identical to Image 1.\n"
            "2. Replace ONLY the clothing. Do not change the background unless it is plain.\n"
            "3. Render each item exactly as shown in its reference image AND as described above "
            "(correct color, fit, silhouette, texture, pattern). Do not invent or substitute any item.\n"
            "4. Ensure all items fit naturally on the person's body — correct layering, proportions, and drape.\n"
            "5. Output: photorealistic full-body fashion portrait, soft studio lighting, sharp focus, high resolution."
        )
    })

    message = Message(role="user", content=content)

    logger.info("wan2.7-image: user=%s items=%s", user_image_url, item_image_urls[:80])
    rsp = ImageGeneration.call(
        model=settings.qwen_wan_model,
        api_key=api_key,
        messages=[message],
        enable_sequential=False,
        n=1,
        size="1024*1024",
    )

    if rsp.status_code != 200:
        return f"Error {rsp.status_code}: {rsp.message}"

    choices = (rsp.output or {}).get("choices") or []
    if not choices:
        return f"No choices in response: {rsp.output}"

    for block in choices[0].get("message", {}).get("content", []):
        img_val = block.get("image", "")
        if img_val.startswith("data:"):
            _, b64 = img_val.split(",", 1)
            _image_result = base64.b64decode(b64)
            return "ok"
        if img_val.startswith("http"):
            with httpx.Client(timeout=30) as client:
                resp = client.get(img_val)
                resp.raise_for_status()
            _image_result = resp.content
            return "ok"

    return f"No image found in response: {choices}"


def _build_agent() -> Agent:
    return Agent(
        name="OutfitImageAgent",
        description="Virtual try-on: dresses a user in selected clothing items using wan2.7-image.",
        instructions=[
            "You are a virtual fashion try-on assistant.",
            "When given a user image URL and item image URLs, call the generate_image tool immediately.",
            "Pass the URLs exactly as provided — do not modify them.",
            "After the tool call completes, reply with a single word: done",
        ],
        tools=[generate_image],
        model=DashScope(
            id=settings.qwen_model,
            api_key=settings.qwen_api_key,
        ),
        markdown=False,
    )


def _run_agent_sync(user_image_url: str, item_image_urls: list[str], items_description: str) -> bytes:
    global _image_result
    _image_result = None

    agent = _build_agent()
    item_urls_str = ",".join(item_image_urls)
    msg = (
        f"Generate a virtual try-on image.\n"
        f"User image URL: {user_image_url}\n"
        f"Item image URLs (comma-separated): {item_urls_str}\n"
        f"Items description: {items_description}"
    )
    response = agent.run(msg)
    logger.info("OutfitImageAgent response content: %s", getattr(response, "content", response))
    logger.info("_image_result set: %s", _image_result is not None)

    if _image_result is None:
        raise RuntimeError(
            f"OutfitImageAgent did not produce an image. Agent response: {response}"
        )
    return _image_result


async def generate_outfit_image(
    user_image_url: str,
    item_image_urls: list[str],
    items_description: str,
) -> bytes:
    """Dress the user in the given items via wan2.7-image. Returns PNG bytes."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor, _run_agent_sync, user_image_url, item_image_urls, items_description
    )
