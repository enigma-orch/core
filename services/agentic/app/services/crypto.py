"""Symmetric encryption for secrets at rest (OAuth tokens, etc.).

If `settings.token_encryption_key` is set to a valid Fernet key, all
write/read operations route through it. If unset (development), values
pass through unchanged and a warning is logged once.

Stored values are tagged with a `fernet:` prefix so we can transparently
migrate existing plaintext rows: anything without the prefix is returned
as-is, anything with the prefix is decrypted.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

_PREFIX = "fernet:"


@lru_cache(maxsize=1)
def _cipher() -> Fernet | None:
    key = settings.token_encryption_key
    if not key:
        logger.warning(
            "token_encryption_key is empty — OAuth tokens will be stored as plaintext. "
            "Set TOKEN_ENCRYPTION_KEY in production."
        )
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        logger.error("Invalid token_encryption_key (must be a urlsafe-base64 32-byte key): %s", exc)
        raise


def encrypt(value: str | None) -> str | None:
    """Encrypt a string for DB storage. None passes through."""
    if value is None:
        return None
    cipher = _cipher()
    if cipher is None:
        return value
    return _PREFIX + cipher.encrypt(value.encode()).decode()


def decrypt(value: str | None) -> str | None:
    """Decrypt a DB value. Plaintext (no prefix) is returned as-is so existing
    rows still work after the encryption rollout."""
    if value is None:
        return None
    if not value.startswith(_PREFIX):
        return value
    cipher = _cipher()
    if cipher is None:
        # We have ciphertext but no key — refuse rather than return junk.
        raise RuntimeError(
            "Encountered encrypted token but token_encryption_key is unset. "
            "Restore the encryption key or re-run the OAuth flow."
        )
    try:
        return cipher.decrypt(value[len(_PREFIX):].encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Encrypted token failed to decrypt — wrong key?") from exc
