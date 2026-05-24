import uuid

from pydantic import BaseModel


class VibeOut(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    description: str | None
    emoji: str | None

    model_config = {"from_attributes": True}


class ColorPaletteOut(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    swatches: list[str]

    model_config = {"from_attributes": True}


class StoreOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    logo_url: str | None
    website_url: str | None

    model_config = {"from_attributes": True}


class SizeOut(BaseModel):
    id: uuid.UUID
    slug: str
    label: str

    model_config = {"from_attributes": True}


class SizeCatalogOut(BaseModel):
    """All available sizes grouped by category."""
    tops: list[SizeOut]
    bottoms: list[SizeOut]
    shoes: list[SizeOut]
    outerwear: list[SizeOut]
