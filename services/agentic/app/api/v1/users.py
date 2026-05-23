"""User profile endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.user import UserMeOut
from app.services.jwt import get_current_user_id_verified

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserMeOut, summary="Get the authenticated user's full profile")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
):
    user = await db.get(User, current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserMeOut.from_user(user)
