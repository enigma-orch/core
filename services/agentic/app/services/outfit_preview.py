"""Shared helper for building the structured item description injected into
outfit image generation prompts (used by both the compose endpoint and the
shuffle prefetch worker).
"""
from __future__ import annotations

from app.models.item import Item


def build_items_description(items: list[Item]) -> str:
    """Serialize item DB metadata into the ground-truth block fed to wan2.7-image."""
    lines = []
    for i, item in enumerate(items, start=1):
        colors = ", ".join(item.colors or []) or "unknown color"
        tags = ", ".join(item.style_tags or [])
        parts = [
            f"Item {i}: {item.name or item.category}",
            f"  category: {item.category}",
            f"  subcategory: {item.subcategory or 'N/A'}",
            f"  colors: {colors}",
            f"  pattern: {item.pattern or 'solid'}",
            f"  fit/style: {tags or 'N/A'}",
            f"  vibe: {item.vibe or 'N/A'}",
        ]
        lines.append("\n".join(parts))
    return "\n\n".join(lines)
