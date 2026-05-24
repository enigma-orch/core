"""User profile endpoints."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.storage import upload_file
from app.models.user import User
from app.schemas.user import UserMeOut
from app.services.jwt import get_current_user_id_verified

router = APIRouter(prefix="/users", tags=["users"])

AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
AVATAR_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _avatar_storage_url(base_url: str, key: str) -> str:
    return f"{base_url}/api/v1/wardrobe/files/{key}"


@router.get("/me", response_model=UserMeOut, summary="Get the authenticated user's full profile")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
):
    user = await db.get(User, current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserMeOut.from_user(user)


@router.patch("/me/avatar", response_model=UserMeOut, summary="Upload or replace the user's profile photo")
async def upload_avatar(
    request: Request,
    image: UploadFile = File(..., description="Profile photo (JPEG, PNG, or WEBP, max 5 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
):
    if image.content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{image.content_type}'. Allowed: JPEG, PNG, WEBP.",
        )

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5 MB.")

    ext = (image.content_type or "image/jpeg").split("/")[-1].replace("jpeg", "jpg")
    key = f"avatars/{current_user_id}/{uuid.uuid4()}.{ext}"
    upload_file(key, data, content_type=image.content_type or "image/jpeg", bucket=request.app.state.rustfs_bucket)

    avatar_url = _avatar_storage_url(str(request.base_url).rstrip("/"), key)

    user = await db.get(User, current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(user)

    return UserMeOut.from_user(user)

