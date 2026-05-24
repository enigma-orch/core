from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ALLOWED_AGENT_MODEL = "qwen3.6-flash"

# Values that look like "unset" — used by both _is_dev_default and the
# non-development validator to decide whether a placeholder slipped through.
_DEFAULT_SECRETS = {"", "change-me", "change-me-in-production", "your-secret-key"}
_DEFAULT_DB_URL = "postgresql+asyncpg://drip:drip@localhost:5432/drip"


def _is_unset(value: str) -> bool:
    return not value or value.strip() in _DEFAULT_SECRETS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    app_debug: bool = True
    secret_key: str = "change-me"
    # Public-facing base URL used by background workers that need to build
    # absolute URLs (e.g. shuffle prefetch preview links). Must not have a
    # trailing slash.
    public_url: str = "http://localhost:8000"
    # Fernet-encoded 32-byte key used to encrypt OAuth tokens at rest.
    # Empty in dev means tokens are stored plaintext (logged as a warning).
    # Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    token_encryption_key: str = ""
    # Comma-separated list of allowed CORS origins. Use "*" only in development.
    cors_origins: str = "*"
    # Comma-separated list of hosts trusted for X-Forwarded-* headers, or "*".
    proxy_trusted_hosts: str = "*"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://drip:drip@localhost:5432/drip"

    # RustFS / S3
    rustfs_endpoint: str = "http://localhost:9000"
    rustfs_public_url: str = "http://localhost:9000"
    rustfs_bucket: str = "drip-bucket"
    aws_access_key_id: str = "drip-access-key"
    aws_secret_access_key: str = "drip-secret-key"
    aws_default_region: str = "us-east-1"

    # Spotify OAuth
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:8000/api/v1/auth/spotify/callback"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Qwen (DashScope) — wardrobe detection agent
    qwen_api_key: str = ""
    qwen_model: str = _ALLOWED_AGENT_MODEL
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    # Qwen Wan — outfit image generation (separate key and model)
    qwen_wan_api_key: str = ""
    qwen_wan_model: str = "wan2.7-image"
    qwen_wan_base_http_url: str = "https://dashscope-intl.aliyuncs.com/api/v1"

    # Google Custom Search
    google_api_key: str = ""
    google_cse_id: str = ""

    # Remove.bg
    remove_bg_api_key: str = ""
    remove_bg_endpoint: str = "https://api.remove.bg/v1.0/removebg"

    # OpenAI / Anthropic (other features only)
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    @field_validator("qwen_model")
    @classmethod
    def validate_qwen_model(cls, v: str) -> str:
        if v != _ALLOWED_AGENT_MODEL:
            raise ValueError(
                f"qwen_model must be '{_ALLOWED_AGENT_MODEL}', got '{v}'. "
                "No other model is permitted by project rules."
            )
        return v

    @model_validator(mode="after")
    def validate_required(self):
        """Fail fast when any required env var is missing or still set to a placeholder.

        These checks run in every environment — development included — because
        missing keys cause silent runtime failures (image generation silently
        skipped, tokens stored unencrypted, etc.) that are much harder to debug
        than a clear startup error.

        Required in all environments:
          - SECRET_KEY          — JWTs are forgeable with the default value.
          - TOKEN_ENCRYPTION_KEY — OAuth / refresh tokens are written via
                                   EncryptedString; missing = plaintext in DB.
          - DATABASE_URL        — no DB, no app.
          - QWEN_API_KEY        — every wardrobe upload and enrichment call.
          - QWEN_WAN_API_KEY    — shuffle preview image generation.
          - REMOVE_BG_API_KEY   — background removal on every uploaded item.
          - AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY — RustFS file storage.

        Required only outside development:
          - CORS_ORIGINS must not be the wildcard `*`.
        """
        missing: list[str] = []

        # ── Always required ───────────────────────────────────────────────────
        if _is_unset(self.secret_key):
            missing.append(
                "SECRET_KEY — must be a strong random string "
                "(e.g. `openssl rand -hex 32`)"
            )
        if _is_unset(self.token_encryption_key):
            missing.append(
                "TOKEN_ENCRYPTION_KEY — Fernet key for encrypting OAuth tokens; "
                "generate with: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        if not self.database_url:
            missing.append("DATABASE_URL")
        if _is_unset(self.qwen_api_key):
            missing.append("QWEN_API_KEY — required for wardrobe item detection and enrichment")
        if _is_unset(self.qwen_wan_api_key):
            missing.append("QWEN_WAN_API_KEY — required for shuffle outfit preview image generation")
        if _is_unset(self.remove_bg_api_key):
            missing.append("REMOVE_BG_API_KEY — required for clothing background removal on upload")
        if _is_unset(self.aws_access_key_id):
            missing.append("AWS_ACCESS_KEY_ID — required for RustFS / S3 file storage")
        if _is_unset(self.aws_secret_access_key):
            missing.append("AWS_SECRET_ACCESS_KEY — required for RustFS / S3 file storage")

        # ── Production only ───────────────────────────────────────────────────
        env = self.app_env.lower()
        if env not in ("development", "dev", "test", "testing"):
            if self.cors_origins.strip() == "*":
                missing.append("CORS_ORIGINS — wildcard `*` is not allowed outside development")

        if missing:
            joined = "\n  - ".join(missing)
            raise RuntimeError(
                f"Cannot start — {len(missing)} required environment variable(s) are missing "
                f"or still set to placeholder values:\n\n  - {joined}\n\n"
                "Copy .env.example to .env and fill in the missing values."
            )
        return self


settings = Settings()
