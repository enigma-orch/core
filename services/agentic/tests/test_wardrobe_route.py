"""Route tests for POST /api/v1/wardrobe/upload."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.wardrobe import DetectedClothingItem, DetectedOutfit

FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

DETECTED_OUTFIT = DetectedOutfit(
    name="Test Outfit",
    summary="A test outfit",
    mood="relaxed",
    vibe="casual",
    season="spring",
    occasion="casual",
    items=[
        DetectedClothingItem(
            name="White T-shirt",
            category="top",
            subcategory="t-shirt",
            colors=["white"],
            style_tags=["minimal"],
            season=["spring", "summer"],
            occasion="casual",
            vibe="minimal",
            mood="fresh",
            size="estimated medium",
            confidence=0.95,
            search_query="white plain t-shirt crew neck",
        )
    ],
)

FAKE_EMBEDDING = [0.01] * 768


@pytest.fixture
def mock_externals():
    """Mock all external calls: remove.bg, Gemini, RustFS, embeddings, DB."""
    with (
        patch("app.api.v1.wardrobe.remove_bg", new_callable=AsyncMock, return_value=FAKE_PNG),
        patch("app.api.v1.wardrobe.detect_outfit", new_callable=AsyncMock, return_value=DETECTED_OUTFIT),
        patch("app.api.v1.wardrobe.emb_svc.embed", new_callable=AsyncMock, return_value=FAKE_EMBEDDING),
        patch("app.api.v1.wardrobe.upload_file"),
        patch("app.api.v1.wardrobe.delete_file"),
    ):
        yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestUploadValidation:
    def test_no_images_returns_400(self, client, mock_externals):
        resp = client.post("/api/v1/wardrobe/upload", files=[])
        assert resp.status_code in (400, 422)

    def test_invalid_content_type_returns_415(self, client, mock_externals):
        resp = client.post(
            "/api/v1/wardrobe/upload",
            files=[("images", ("test.txt", b"hello", "text/plain"))],
        )
        assert resp.status_code == 415

    def test_file_too_large_returns_400(self, client, mock_externals):
        big = b"\x00" * (11 * 1024 * 1024)
        resp = client.post(
            "/api/v1/wardrobe/upload",
            files=[("images", ("big.png", big, "image/png"))],
        )
        assert resp.status_code == 400


class TestUploadSuccess:
    def test_returns_list(self, client, mock_externals):
        resp = client.post(
            "/api/v1/wardrobe/upload",
            files=[("images", ("outfit.png", FAKE_PNG, "image/png"))],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)

    def test_outfit_has_required_fields(self, client, mock_externals):
        resp = client.post(
            "/api/v1/wardrobe/upload",
            files=[("images", ("outfit.png", FAKE_PNG, "image/png"))],
        )
        assert resp.status_code == 200
        outfit = resp.json()[0]
        assert "id" in outfit
        assert "items" in outfit
        assert "preview_image_url" in outfit
        assert "embedding" in outfit

    def test_items_have_embeddings(self, client, mock_externals):
        resp = client.post(
            "/api/v1/wardrobe/upload",
            files=[("images", ("outfit.png", FAKE_PNG, "image/png"))],
        )
        assert resp.status_code == 200
        items = resp.json()[0]["items"]
        assert len(items) > 0
        for item in items:
            assert item["embedding"] is not None
            assert len(item["embedding"]) == 768

    def test_outfit_embedding_is_768_dims(self, client, mock_externals):
        resp = client.post(
            "/api/v1/wardrobe/upload",
            files=[("images", ("outfit.png", FAKE_PNG, "image/png"))],
        )
        assert resp.status_code == 200
        outfit = resp.json()[0]
        assert len(outfit["embedding"]) == 768

    def test_multiple_images_return_multiple_outfits(self, client, mock_externals):
        resp = client.post(
            "/api/v1/wardrobe/upload",
            files=[
                ("images", ("a.png", FAKE_PNG, "image/png")),
                ("images", ("b.png", FAKE_PNG, "image/png")),
            ],
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_source_is_manual_upload(self, client, mock_externals):
        resp = client.post(
            "/api/v1/wardrobe/upload",
            files=[("images", ("outfit.png", FAKE_PNG, "image/png"))],
        )
        assert resp.status_code == 200
        assert resp.json()[0]["source"] == "manual_upload"

    def test_items_have_image_urls(self, client, mock_externals):
        resp = client.post(
            "/api/v1/wardrobe/upload",
            files=[("images", ("outfit.png", FAKE_PNG, "image/png"))],
        )
        assert resp.status_code == 200
        item = resp.json()[0]["items"][0]
        assert item["original_image_url"] is not None
        assert item["clean_image_url"] is not None


class TestAgentModel:
    def test_agent_uses_qwen3_6_flash(self):
        from app.config import settings
        assert settings.qwen_model == "qwen3.6-flash"

    def test_config_rejects_wrong_model(self):
        import pytest
        from pydantic import ValidationError
        from app.config import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings(qwen_model="gpt-4o", _env_file=None)

    def test_item_embedding_is_768_dims(self):
        from app.services.embeddings import _DIMS
        assert _DIMS == 768

    def test_outfit_embedding_is_768_dims(self):
        from app.services.embeddings import _DIMS
        assert _DIMS == 768


class TestMalformedAgentOutput:
    def test_malformed_json_returns_500(self, client, mock_externals):
        from unittest.mock import patch

        with patch(
            "app.api.v1.wardrobe.detect_outfit",
            new_callable=AsyncMock,
            side_effect=ValueError("DeepSeek failed to return valid DetectedOutfit"),
        ):
            resp = client.post(
                "/api/v1/wardrobe/upload",
                files=[("images", ("outfit.png", FAKE_PNG, "image/png"))],
            )
        assert resp.status_code == 500


class TestEmbeddingValidation:
    def test_wrong_dims_raises(self):
        from app.services.embeddings import _validate
        import pytest
        with pytest.raises(ValueError, match="768"):
            _validate([0.1] * 512)

    def test_non_finite_raises(self):
        import math
        from app.services.embeddings import _validate
        import pytest
        values = [0.1] * 768
        values[10] = math.inf
        with pytest.raises(ValueError, match="finite"):
            _validate(values)

    def test_valid_embedding_passes(self):
        from app.services.embeddings import _validate
        values = [0.01] * 768
        assert len(_validate(values)) == 768
