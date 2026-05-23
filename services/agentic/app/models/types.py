"""Custom SQLAlchemy column types."""
from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.services.crypto import decrypt, encrypt


class EncryptedString(TypeDecorator):
    """Transparently Fernet-encrypts a string at write time, decrypts at read.

    Plaintext rows (no `fernet:` prefix) pass through unchanged, so existing
    rows keep working until they're rewritten by the next OAuth refresh.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        return encrypt(value)

    def process_result_value(self, value, dialect):  # type: ignore[override]
        return decrypt(value)
