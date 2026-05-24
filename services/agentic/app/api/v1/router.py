from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.users import router as users_router
from app.api.v1.wardrobe import router as wardrobe_router
from app.api.v1.items import router as items_router
from app.api.v1.outfits import router as outfits_router
from app.api.v1.outfit_compose import router as outfit_compose_router
from app.api.v1.discover import router as discover_router
from app.api.v1.galleries import router as galleries_router
from app.api.v1.shuffle import router as shuffle_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.outfit_complete import router as outfit_complete_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(onboarding_router)
router.include_router(users_router)
router.include_router(wardrobe_router)
router.include_router(items_router)
router.include_router(outfits_router)
router.include_router(outfit_compose_router)
router.include_router(discover_router)
router.include_router(galleries_router)
router.include_router(shuffle_router)
router.include_router(calendar_router)
router.include_router(outfit_complete_router)


@router.get("/ping")
async def ping():
    return {"message": "pong"}
