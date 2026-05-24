import asyncio
import logging
from contextlib import asynccontextmanager

from app.utils.logging import RequestIdMiddleware, configure_logging

configure_logging()

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.infrastructure.database import engine
from app.infrastructure.storage import ensure_bucket
from app.services.background_removal import init_rembg_session
from app.workers.spotify_sync import sync_all_users
from app.workers.outfit_scraper_sync import scheduled_scrape_all_users
from app.workers.shuffle_prefetch import scheduled_shuffle_prefetch

logger = logging.getLogger(__name__)


def _ensure_bucket_with_retry(bucket: str, retries: int = 1, delay: float = 0.5) -> None:
    import time
    for attempt in range(1, retries + 1):
        try:
            ensure_bucket(bucket)
            return
        except Exception as exc:
            if attempt == retries:
                raise
            logger.warning("RustFS not ready (attempt %d/%d): %s — retrying in %.0fs", attempt, retries, exc, delay)
            time.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()

    try:
        await loop.run_in_executor(None, _ensure_bucket_with_retry, settings.rustfs_bucket)
        app.state.rustfs_bucket = settings.rustfs_bucket
    except Exception as exc:
        logger.warning("RustFS unavailable (object storage disabled): %s", exc)
        app.state.rustfs_bucket = None

    # Warm the local rembg fallback session so the first upload doesn't pay
    # the ONNX cold-start cost. Failure is non-fatal — primary backend stays
    # remove.bg.
   # app.state.rembg_session = await loop.run_in_executor(None, init_rembg_session)

    # Start background Spotify sync scheduler (every 24 hours)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sync_all_users, "interval", hours=24, id="spotify_sync")
    # Fire once immediately on startup so no one waits 24h for first sync
    async def _sync_all_safe() -> None:
        try:
            await sync_all_users()
        except Exception as exc:
            logger.warning("Startup Spotify sync failed (non-fatal): %s", exc)

    asyncio.create_task(_sync_all_safe())
    # Scrape outfits every 60 minutes
    scheduler.add_job(scheduled_scrape_all_users, "interval", minutes=60, id="outfit_scraper")
    scheduler.add_job(scheduled_shuffle_prefetch, "interval", minutes=10, id="shuffle_prefetch")
    scheduler.start()
    app.state.scheduler = scheduler

    yield

    scheduler.shutdown(wait=False)
    await engine.dispose()


app = FastAPI(
    title="Drip",
    version="0.1.0",
    lifespan=lifespan,
)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.proxy_trusted_hosts)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
