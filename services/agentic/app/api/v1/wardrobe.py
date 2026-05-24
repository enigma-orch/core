import uuid as _uuid_mod
from pathlib import Path

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.wardrobe_agent import detect_item
from app.infrastructure.database import get_db
from app.infrastructure.storage import delete_file, download_file, upload_file
from app.models.item import Item
from app.schemas.wardrobe import (
    ErrorResponse,
    ItemUploadOut,
    RemoveBackgroundResponse,
)
from app.services.background_removal import ALLOWED_CONTENT_TYPES, MAX_BYTES, remove_bg
from app.services import embeddings as emb_svc
from app.services.jwt import get_current_user_id

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _storage_url(base_url: str, key: str) -> str:
    return f"{base_url}/api/v1/wardrobe/files/{key}"


def _orig_key(data: bytes, filename: str | None) -> str:
    ext = Path(filename).suffix.lstrip(".").lower() if filename else "png"
    ext = ext if ext in {"jpg", "jpeg", "png", "webp"} else "png"
    return f"wardrobe/original/{_uuid_mod.uuid4()}.{ext}"


# ── Standalone background removal endpoint ────────────────────────────────────

@router.post(
    "/remove-background",
    response_model=RemoveBackgroundResponse,
    responses={413: {"model": ErrorResponse}, 415: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def remove_background_endpoint(
    request: Request,
    image: UploadFile,
    current_user_id: str = Depends(get_current_user_id),
) -> RemoveBackgroundResponse:
    data = await image.read()
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail={"error": "Unsupported media type", "detail": f"Accepted: {', '.join(ALLOWED_CONTENT_TYPES)}"},
        )
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail={"error": "File too large", "detail": "Max 10 MB"})

    try:
        png_bytes = await remove_bg(data)
        key = f"wardrobe/no-bg/{_uuid_mod.uuid4()}.png"
        upload_file(key, png_bytes, content_type="image/png", bucket=request.app.state.rustfs_bucket)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "Processing failed", "detail": str(exc)})

    base = str(request.base_url).rstrip("/")
    return RemoveBackgroundResponse(url=_storage_url(base, key))


# ── File serving ──────────────────────────────────────────────────────────────

@router.get(
    "/files/{key:path}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}, 404: {"model": ErrorResponse}},
)
async def serve_file(key: str, request: Request) -> Response:
    try:
        data = download_file(key, request.app.state.rustfs_bucket)
    except Exception:
        raise HTTPException(status_code=404, detail={"error": "File not found"})
    content_type = "image/png" if key.endswith(".png") else "image/jpeg"
    return Response(content=data, media_type=content_type)


# ── Simple photo upload (no AI, no wardrobe item) ────────────────────────────

@router.post("/upload-photo", response_model=dict)
async def upload_photo(
    request: Request,
    image: UploadFile,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """Store an image in RustFS and return its URL. No AI processing."""
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail={"error": f"Unsupported type '{image.content_type}'"})
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail={"error": "Empty file"})
    key = f"photos/{_uuid_mod.uuid4()}.jpg"
    upload_file(key, data, content_type=image.content_type or "image/jpeg", bucket=request.app.state.rustfs_bucket)
    url = _storage_url(str(request.base_url).rstrip("/"), key)
    return {"url": url}


# ── Multi-image upload ────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=list[ItemUploadOut],
    responses={
        400: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["images"],
                        "properties": {
                            "images": {
                                "type": "array",
                                "items": {"type": "string", "format": "binary"},
                                "description": "One or more clothing images (JPEG, PNG, WEBP)",
                            }
                        },
                    }
                }
            },
        }
    },
)
async def upload_wardrobe_images(
    request: Request,
    images: Annotated[list[UploadFile], File(description="One or more clothing item images (JPEG, PNG, WEBP)")],
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> list[ItemUploadOut]:
    user_id = _uuid_mod.UUID(current_user_id)
    bucket = request.app.state.rustfs_bucket
    base_url = str(request.base_url).rstrip("/")

    # ── Validate all images before any work ──────────────────────────────────
    if not images:
        raise HTTPException(status_code=400, detail={"error": "No images provided"})

    validated: list[tuple[UploadFile, bytes]] = []
    for img in images:
        if img.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail={"error": f"Unsupported type '{img.content_type}'", "detail": f"Accepted: {', '.join(ALLOWED_CONTENT_TYPES)}"},
            )
        data = await img.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(status_code=400, detail={"error": f"File '{img.filename}' exceeds 10 MB limit"})
        if not data:
            raise HTTPException(status_code=400, detail={"error": f"File '{img.filename}' is empty"})
        validated.append((img, data))

    # ── Process each image → one Item per image ───────────────────────────────
    uploaded_keys: list[str] = []
    saved_items: list[Item] = []

    try:
        for upload, raw_bytes in validated:
            # 1. Upload original to RustFS
            orig_key = _orig_key(raw_bytes, upload.filename)
            upload_file(orig_key, raw_bytes, content_type=upload.content_type or "image/png", bucket=bucket)
            uploaded_keys.append(orig_key)
            original_url = _storage_url(base_url, orig_key)

            # 2. Remove background
            clean_bytes = await remove_bg(raw_bytes)
            clean_key = f"wardrobe/no-bg/{_uuid_mod.uuid4()}.png"
            upload_file(clean_key, clean_bytes, content_type="image/png", bucket=bucket)
            uploaded_keys.append(clean_key)
            clean_url = _storage_url(base_url, clean_key)

            # 3. Detect single clothing item with Qwen
            det = await detect_item(raw_bytes)

            # 4. Generate embedding
            item_emb = await emb_svc.embed(emb_svc.item_text(det.model_dump()))

            # 5. Persist Item
            item = Item(
                user_id=user_id,
                original_image_url=original_url,
                clean_image_url=clean_url,
                name=det.name,
                category=det.category,
                subcategory=det.subcategory,
                brand=det.brand,
                colors=det.colors,
                season=det.season,
                occasion=det.occasion,
                style_tags=det.style_tags,
                pattern=det.pattern,
                vibe=det.vibe,
                mood=det.mood,
                size=det.size,
                enriched=True,
                enrichment_data={
                    "confidence": det.confidence,
                    "search_query": det.search_query,
                },
                embedding=item_emb,
            )
            db.add(item)
            await db.flush()
            await db.refresh(item)
            saved_items.append(item)

    except HTTPException:
        raise
    except Exception as exc:
        for key in uploaded_keys:
            try:
                delete_file(key, bucket)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail={"error": "Processing failed", "detail": str(exc)})

    return [ItemUploadOut.model_validate(item) for item in saved_items]
