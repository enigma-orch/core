"""Unit tests for the remove.bg background removal service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.background_removal import remove_bg, process_image, ALLOWED_CONTENT_TYPES, MAX_BYTES


FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture
def mock_upload():
    with patch("app.services.background_removal.upload_file") as m:
        m.return_value = "wardrobe/no-bg/test.png"
        yield m


class TestRemoveBg:
    async def test_success(self):
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.content = FAKE_PNG
        mock_resp.status_code = 200

        with patch("app.services.background_removal.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_settings.remove_bg_api_key = "test-key"
            mock_settings.remove_bg_endpoint = "https://api.remove.bg/v1.0/removebg"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await remove_bg(b"fake-image-bytes")
            assert result == FAKE_PNG

    async def test_missing_api_key_raises(self):
        with patch("app.services.background_removal.settings") as mock_settings:
            mock_settings.remove_bg_api_key = ""
            with pytest.raises(RuntimeError, match="REMOVE_BG_API_KEY"):
                await remove_bg(b"fake-image-bytes")

    async def test_402_quota_exceeded(self):
        mock_resp = MagicMock()
        mock_resp.is_success = False
        mock_resp.status_code = 402

        with patch("app.services.background_removal.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_settings.remove_bg_api_key = "test-key"
            mock_settings.remove_bg_endpoint = "https://api.remove.bg/v1.0/removebg"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="quota"):
                await remove_bg(b"fake-image-bytes")

    async def test_non_success_status(self):
        mock_resp = MagicMock()
        mock_resp.is_success = False
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("app.services.background_removal.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_settings.remove_bg_api_key = "test-key"
            mock_settings.remove_bg_endpoint = "https://api.remove.bg/v1.0/removebg"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="500"):
                await remove_bg(b"fake-image-bytes")

    async def test_empty_response_raises(self):
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.content = b""
        mock_resp.status_code = 200

        with patch("app.services.background_removal.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_settings.remove_bg_api_key = "test-key"
            mock_settings.remove_bg_endpoint = "https://api.remove.bg/v1.0/removebg"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="empty"):
                await remove_bg(b"fake-image-bytes")

    async def test_timeout_raises(self):
        with patch("app.services.background_removal.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_settings.remove_bg_api_key = "test-key"
            mock_settings.remove_bg_endpoint = "https://api.remove.bg/v1.0/removebg"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="timed out"):
                await remove_bg(b"fake-image-bytes")


class TestProcessImage:
    async def test_uploads_and_returns_key(self, mock_upload):
        with patch("app.services.background_removal.remove_bg", new_callable=AsyncMock) as mock_rm:
            mock_rm.return_value = FAKE_PNG
            key = await process_image(b"fake-bytes", "test-bucket")
            assert key.startswith("wardrobe/no-bg/")
            assert key.endswith(".png")
            mock_upload.assert_called_once()


class TestConstants:
    def test_allowed_content_types(self):
        assert "image/jpeg" in ALLOWED_CONTENT_TYPES
        assert "image/png" in ALLOWED_CONTENT_TYPES
        assert "image/webp" in ALLOWED_CONTENT_TYPES

    def test_max_bytes_is_10mb(self):
        assert MAX_BYTES == 10 * 1024 * 1024
