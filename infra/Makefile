# ─────────────────────────────────────────────────────────────────────────────
# infra — shared services + database schema source-of-truth for the enigma
# stack. Both ../agentic and ../backend connect to what this Makefile starts.
# ─────────────────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := help

# Use the local .env so DATABASE_URL and friends are visible to dbmate/psql.
ifneq (,$(wildcard .env))
include .env
export
endif

DBMATE := dbmate --migrations-dir db/migrations --schema-file db/schema.sql

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<target>\033[0m\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Infrastructure (docker compose)

.PHONY: up down restart ps logs nuke graph-up graph-down

up: ## Start postgres + rustfs + redis (waits until postgres is healthy)
	docker compose up -d --wait postgres rustfs redis

down: ## Stop containers (volumes preserved)
	docker compose down

restart: down up ## Restart all infra services

ps: ## Show container status
	docker compose ps

logs: ## Tail logs for all services
	docker compose logs -f

nuke: ## Stop AND remove volumes — destroys local data
	docker compose down -v

graph-up: ## Start optional Neo4j (graph profile, waits until healthy)
	docker compose --profile graph up -d --wait neo4j

graph-down: ## Stop Neo4j
	docker compose stop neo4j

##@ Database migrations (dbmate)

.PHONY: db-up db-down db-status db-new db-dump db-reset

db-up: ## Apply all pending migrations
	$(DBMATE) up

db-down: ## Roll back the latest migration
	$(DBMATE) down

db-status: ## Show applied / pending migrations
	$(DBMATE) status

db-new: ## Create a new migration. Usage: make db-new name=add_widgets
	@test -n "$(name)" || (echo "ERROR: pass name=<slug>"; exit 1)
	$(DBMATE) new $(name)

db-dump: ## Regenerate db/schema.sql from the live DB (uses pg_dump inside container)
	@docker exec enigma_postgres pg_dump \
		-U $${POSTGRES_USER:-drip} -d $${POSTGRES_DB:-drip} \
		--schema-only --no-owner --no-privileges --no-tablespaces \
		| grep -v '^\\restrict\|^\\unrestrict' \
		> db/schema.sql
	@echo "wrote db/schema.sql ($$(wc -l < db/schema.sql) lines)"

db-reset: ## Drop + re-apply every migration from scratch
	$(DBMATE) drop
	$(DBMATE) up

##@ Seeds

.PHONY: seed-dev seed-reset

seed-dev: ## Load db/seeds/dev.sql into the running DB
	psql "$$DATABASE_URL" -f db/seeds/dev.sql

seed-reset: db-reset seed-dev ## Reset DB then load dev seeds
