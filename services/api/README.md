# DRIP Backend

Go/Fiber backend for DRIP's auth, wardrobe, market catalog, outfits, swipe discovery, wishlist, and backend-owned media metadata. The app is wired with Uber Fx for lifecycle-managed startup and shutdown.

## Setup

Shared infrastructure (Postgres + pgvector, Redis, optional Neo4j) and the
database migrations live in [`../../infra`](../../infra). This service connects to
the Postgres that `../../infra` brings up and reads its schema (for sqlc
generation) from `../../infra/db/schema.sql`.

1. Copy `.env.example` to `.env`. Defaults point at the local infra Postgres;
   override `POSTGRES_URL` / `DATABASE_URL` with Neon URLs in cloud envs.
2. Start infra and apply migrations:

```sh
make infra-up                  # docker compose up in ../../infra
make db-up                     # delegates to ../../infra/db/migrations
make seed-dev                  # delegates to ../../infra/db/seeds/dev.sql
```

3. Start the API:

```sh
make dev
```

The temporary auth boundary is `X-User-ID`. Demo seed user:

```text
11111111-1111-1111-1111-111111111111
```

## Useful Commands

```sh
make test
make sqlc
make db-status
make db-new name=add_feature
make seed-reset
```

## Demo Flow

```sh
curl http://localhost:8080/health/live

curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@drip.app","username":"demo","password":"password123"}'

curl -H "X-User-ID: 11111111-1111-1111-1111-111111111111" \
  http://localhost:8080/api/v1/wardrobe/items

curl -H "X-User-ID: 11111111-1111-1111-1111-111111111111" \
  http://localhost:8080/api/v1/store-products

curl -H "X-User-ID: 11111111-1111-1111-1111-111111111111" \
  http://localhost:8080/api/v1/discover/cards

curl -H "X-Internal-Token: change-me-for-shared-environments" \
  "http://localhost:8080/internal/v1/users/11111111-1111-1111-1111-111111111111/recommendation-context"
```

## Boundaries

- User-facing auth routes live under `/api/v1/auth`; wardrobe MVP routes still support temporary `X-User-ID` until they are migrated to JWT middleware.
- Runtime migrations and the schema source-of-truth live in `../../infra`; sqlc reads `../../infra/db/schema.sql` per `sqlc.yaml`.
- Store catalog is seeded demo data; no live scraping.
- Cloudinary images are metadata only in this backend slice.
- Matching/scoring runs, candidate scoring, and tool traces belong to a separate service and database outside this repo.
- Internal endpoints are for service-to-service calls. Configure `INTERNAL_API_TOKEN` outside local development.

## Graph subsystem (optional)

The social graph is mirrored into Neo4j by a transactional-outbox projector
so endpoints like *suggested follows* and *taste-similar users* can be served
by Cypher queries. Postgres remains the source of truth; the projector is
eventually consistent.

Enable locally:

```sh
docker compose -f ../../infra/docker-compose.yaml --profile graph up -d neo4j
export GRAPH_ENABLED=true NEO4J_PASSWORD=change-me
make dev
```

Endpoints (require Bearer JWT):

```text
GET /api/v1/graph/suggested-follows?limit=20
GET /api/v1/graph/mutual/:other_user_id
GET /api/v1/graph/taste-similar?limit=20
```

When `GRAPH_ENABLED=false`, the projector does not start and those endpoints
return `503 Service Unavailable`. The rest of the API is unaffected.
