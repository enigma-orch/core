"""
Embedding service — text-embedding-v3 via Qwen/DashScope OpenAI-compatible API.

All call sites must go through this module so embedding dimensions and model
names are never scattered across the codebase.

DashScope text-embedding-v3 supports configurable output dimensions.
We fix it at 768 to match existing DB migrations.
"""
import asyncio
import logging
import math
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-v3"
_DIMS = 768

_executor = ThreadPoolExecutor(max_workers=2)


def _validate(values: list[float]) -> list[float]:
    if len(values) != _DIMS:
        raise ValueError(f"Expected {_DIMS}-dim embedding, got {len(values)}")
    for i, v in enumerate(values):
        if not isinstance(v, (int, float)):
            raise ValueError(f"Embedding value at index {i} is not numeric: {type(v)}")
        if not math.isfinite(v):
            raise ValueError(f"Embedding value at index {i} is not finite: {v}")
    return values


def _embed_sync(text: str) -> list[float]:
    client = OpenAI(
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
    )
    resp = client.embeddings.create(
        model=_EMBED_MODEL,
        input=text,
        dimensions=_DIMS,
    )
    return _validate(list(resp.data[0].embedding))


async def embed(text: str) -> list[float]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _embed_sync, text)


def item_text(d: dict) -> str:
    colors = ", ".join(d.get("colors") or [])
    tags = ", ".join(d.get("style_tags") or [])
    season = ", ".join(d.get("season") or [])
    return (
        f"{d.get('category', '')} {d.get('name', '')} {d.get('subcategory', '')}. "
        f"Colors: {colors}. Style: {tags}. Season: {season}. "
        f"Occasion: {d.get('occasion', '')}. Vibe: {d.get('vibe', '')}. "
        f"Mood: {d.get('mood', '')}."
    )


def outfit_text(d: dict, member_item_texts: list[str]) -> str:
    items_summary = "; ".join(member_item_texts)
    return (
        f"Outfit: {d.get('name', '')}. {d.get('summary', '')} "
        f"Vibe: {d.get('vibe', '')}. Mood: {d.get('mood', '')}. "
        f"Season: {d.get('season', '')}. Occasion: {d.get('occasion', '')}. "
        f"Items: {items_summary}."
    )
