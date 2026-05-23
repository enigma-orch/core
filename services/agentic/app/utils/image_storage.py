import asyncio
import uuid
from pathlib import Path


async def save_image(image_bytes: bytes, user_id: str) -> str:
    """
    Development: saves PNG to /tmp/drip_uploads/{user_id}/{uuid}.png and
    returns the local file path.

    TODO: replace with S3 upload + CloudFront URL for production.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _save_sync, image_bytes, user_id)


def _save_sync(image_bytes: bytes, user_id: str) -> str:
    upload_dir = Path("/tmp/drip_uploads") / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid.uuid4()}.png"
    dest.write_bytes(image_bytes)
    return str(dest)
