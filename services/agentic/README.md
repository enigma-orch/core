# Drip

FastAPI wardrobe AI app — Gemini 2.0 Flash vision, pgvector embeddings, remove.bg, RustFS storage.

## Local Development

Shared infrastructure (Postgres + pgvector, RustFS, Redis, optional Neo4j) and
the database migrations live in [`../../infra`](../../infra). This service connects
to the Postgres and object store they bring up. The FastAPI app runs directly
on localhost.

```bash
# 1. Start infrastructure
make infra-up                  # alias for: make -C ../../infra up

# 2. Install dependencies
make install

# 3. Copy and fill in your env
cp .env.example .env

# 4. Apply migrations (delegates to ../../infra)
make migrate                   # alias for: make -C ../../infra db-up

# 5. Start the app
make run
```

The app is available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Database

This service no longer ships migrations or a schema file. Everything lives in
[`../../infra/db/`](../../infra/db). To add a new migration:

```bash
make -C ../../infra db-new name=my_change
$EDITOR ../../infra/db/migrations/<ts>_my_change.sql
make -C ../../infra db-up
make -C ../../infra db-dump        # refresh ../../infra/db/schema.sql
```

See [`../../infra/README.md`](../../infra/README.md) for the full source-of-truth
rules and the table ownership matrix.

## Environment Variables

See `.env.example` for all required variables. Key values:

| Variable | Description |
|---|---|
| `SECRET_KEY` | HMAC key used for JWT signing — must NOT be the default outside development |
| `TOKEN_ENCRYPTION_KEY` | Fernet key (urlsafe-base64, 32 bytes) used to encrypt OAuth tokens at rest. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `CORS_ORIGINS` | Comma-separated origins; defaults to `*` for development |
| `DATABASE_URL` | PostgreSQL — points at the local infra Postgres on `localhost:5432` |
| `RUSTFS_ENDPOINT` | RustFS — use `http://localhost:9000` for local dev |
| `QWEN_API_KEY` | DashScope API key (Qwen3.6-flash for vision, wan2.7-image for try-on) |
| `REMOVE_BG_API_KEY` | remove.bg API key for background removal |
