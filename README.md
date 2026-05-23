# enigma

Monorepo for the enigma stack. Three responsibility-scoped folders share a
single Postgres and a single source of truth for the schema.

```
enigma/
├── infra/              # docker-compose (postgres+pgvector, rustfs, redis, neo4j)
│   └── db/             # all dbmate migrations + generated schema.sql + seeds
├── services/
│   ├── agentic/        # Python/FastAPI — iOS-facing AI service (Qwen vision, embeddings)
│   └── api/            # Go/Fiber — REST API for web/Android (auth, social, outfits)
└── Makefile            # top-level orchestrator (delegates to subdir Makefiles)
```

## Quick start

```sh
cp infra/.env.example infra/.env
cp services/agentic/.env.example services/agentic/.env
cp services/api/.env.example     services/api/.env

make bootstrap          # up + db-up + db-dump + api-sqlc
```

Then in two terminals:

```sh
make agentic            # FastAPI on :8000
make api                # Go/Fiber on :8080
```

Run `make` (no args) to see every available target.

## Folder responsibilities

| Folder              | Owns                                                                |
|---------------------|---------------------------------------------------------------------|
| `infra/`            | Docker compose for shared services; all DB migrations; `schema.sql` |
| `infra/db/`         | `migrations/` (dbmate), `schema.sql` (generated), `seeds/`          |
| `services/agentic/` | Python AI service code, FastAPI handlers, SQLAlchemy models         |
| `services/api/`     | Go REST API code, sqlc queries (reads `../../infra/db/schema.sql`)  |

Neither service owns DB schema. All migrations live in `infra/db/migrations/`.
Run `make db-new name=foo`, edit the SQL, `make db-up`, `make db-dump`, then
`make api-sqlc` if the change touches anything the Go service reads.

## Service boundaries

- **`agentic`** connects via `postgresql+asyncpg://drip:drip@127.0.0.1:5432/drip`. It is the iOS app's backend.
- **`api`** connects via `postgresql://drip:drip@127.0.0.1:5432/drip?sslmode=disable`. It serves web/Android and owns the social graph projection (Neo4j outbox).

Both touch the same DB; ownership of *tables* is documented in `infra/README.md`.

## Day-to-day cheatsheet

```sh
make up                 # bring postgres+rustfs+redis online
make db-status          # what migrations are applied
make db-new name=widgets
make db-up
make db-dump            # regenerate infra/db/schema.sql
make api-sqlc           # regenerate Go types after schema change
make test               # run service tests
make down               # stop containers (data preserved)
make nuke               # destroy local volumes
```

## Schema-change workflow

1. `make db-new name=add_widgets` — scaffolds `infra/db/migrations/<ts>_add_widgets.sql`.
2. Edit the SQL.
3. `make db-up && make db-dump` — applies + refreshes the schema dump.
4. If `services/api` reads the new shape, `make api-sqlc` and update any handwritten code in `services/api/internal/repository/`.
5. If `services/agentic` reads the new shape, add/update SQLAlchemy models in `services/agentic/app/models/`.
6. Commit the migration, the regenerated `schema.sql`, and any sqlc/SQLAlchemy changes together.
