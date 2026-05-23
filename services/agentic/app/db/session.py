"""
Canonical DB session location.
Implementation lives in app/infrastructure/database.py — re-exported here
so both import paths work.
"""

from app.infrastructure.database import AsyncSessionLocal, engine, get_db  # noqa: F401

__all__ = ["engine", "AsyncSessionLocal", "get_db"]
