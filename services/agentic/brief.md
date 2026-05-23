# Drip — Project Brief

## Structure

```
drip/
├── Dockerfile                   # UV-based Python 3.12 image
├── docker-compose.yml           # postgres · qdrant · rustfs · app
├── pyproject.toml               # UV project with all deps
├── .env.example                 # Copy to .env before running
└── app/
    ├── main.py                  # FastAPI app + lifespan (runs migrations)
    ├── config.py                # Pydantic Settings (reads .env)
    ├── api/v1/router.py         # Route entrypoint — add sub-routers here
    ├── agents/base.py           # build_agent() factory using agno + OpenAI
    ├── tools/                   # Drop agno Tool subclasses here
    ├── infrastructure/
    │   ├── database.py          # Async SQLAlchemy engine + get_db() dep
    │   ├── qdrant.py            # Async Qdrant client + ensure_collection()
    │   └── storage.py           # boto3 → RustFS (S3-compat) upload/download
    ├── models/base.py           # DeclarativeBase + UUIDMixin + TimestampMixin
    └── schemas/base.py          # Pydantic BaseSchema + UUID/Timestamp mixins
```

## Start everything

```bash
cp .env.example .env          # fill in your API keys
docker compose up --build
```

## New feature workflow

1. Add a SQLAlchemy model in `app/models/`
2. Add a Pydantic schema in `app/schemas/`
3. Add an agno tool in `app/tools/` using `build_agent()` from `app/agents/base.py`
4. Wire a route in `app/api/v1/router.py`

## Services

| Service  | Port        | Purpose                        |
|----------|-------------|--------------------------------|
| app      | 8000        | FastAPI application            |
| postgres | 5432        | Relational data (SQLAlchemy)   |
| qdrant   | 6333 / 6334 | Vector store (HTTP / gRPC)     |
| rustfs   | 9000 / 9001 | Object storage (S3-compatible) |

## Key packages

| Package           | Role                              |
|-------------------|-----------------------------------|
| fastapi           | Web framework                     |
| uvicorn           | ASGI server                       |
| agno              | Agentic AI framework              |
| sqlalchemy        | Async ORM (asyncpg driver)        |
| alembic           | DB migrations                     |
| qdrant-client     | Vector DB client                  |
| boto3             | S3 client → RustFS                |
| pydantic-settings | Settings from .env                |
| python-dotenv     | .env loader                       |

> **RustFS note:** image tag is `rustfs/rustfs:latest`. It is S3-compatible so `storage.py` uses boto3 unchanged.
