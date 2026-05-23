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
        """Fail fast when required env is missing.

        Dev and test environments stay permissive so the app and pytest can
        boot without a full secret bundle (tests typically mock external
        services). Outside development, the validator refuses to start:

        - SECRET_KEY must not be the default — JWTs would be forgeable.
        - TOKEN_ENCRYPTION_KEY must be a real Fernet key — refresh tokens
          and OAuth tokens are written through EncryptedString.
        - DATABASE_URL must not be the local dev default.
        - QWEN_API_KEY must be set — every upload/compose call needs it.
        - CORS_ORIGINS must be narrowed; `*` is dev-only.
        """
        env = self.app_env.lower()
        if env in ("development", "dev", "test", "testing"):
            return self

        missing: list[str] = []
        if _is_unset(self.secret_key):
            missing.append("SECRET_KEY (must be a strong random value, not the default)")
        if _is_unset(self.token_encryption_key):
            missing.append(
                "TOKEN_ENCRYPTION_KEY (Fernet key — generate with "
                "`python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\"`)"
            )
        if not self.database_url or self.database_url == _DEFAULT_DB_URL:
            missing.append("DATABASE_URL (still pointing at the local dev default)")
        if _is_unset(self.qwen_api_key):
            missing.append("QWEN_API_KEY")
        if self.cors_origins.strip() == "*":
            missing.append("CORS_ORIGINS (refuse to run with wildcard outside development)")

        if missing:
            joined = "\n  - ".join(missing)
            raise RuntimeError(
                "Refusing to start — required configuration is missing:\n  - "
                f"{joined}\n\nSee .env.example for the full list."
            )
        return self


settings = Settings()
