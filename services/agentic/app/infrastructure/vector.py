from typing import Literal

from pgvector.sqlalchemy import Vector
from sqlalchemy import text

from app.infrastructure.database import engine

DistanceOp = Literal["vector_cosine_ops", "vector_l2_ops", "vector_ip_ops"]


async def ensure_extension() -> None:
    """Enable pgvector extension — idempotent, safe to call on every startup."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


async def ensure_vector_index(
    table: str,
    column: str,
    distance: DistanceOp = "vector_cosine_ops",
    lists: int = 100,
) -> None:
    """Create an IVFFlat index on a vector column — idempotent."""
    index_name = f"{table}_{column}_ivfflat_idx"
    sql = (
        f"CREATE INDEX IF NOT EXISTS {index_name} "
        f"ON {table} USING ivfflat ({column} {distance}) "
        f"WITH (lists = {lists})"
    )
    async with engine.begin() as conn:
        await conn.execute(text(sql))


__all__ = ["Vector", "ensure_extension", "ensure_vector_index", "DistanceOp"]
