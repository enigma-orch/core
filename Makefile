# ─────────────────────────────────────────────────────────────────────────────
# enigma — monorepo root.
# Orchestrates shared infra (infra/) and the two services (services/agentic,
# services/api). Each subdir has its own Makefile; this file only delegates.
# ─────────────────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<target>\033[0m\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Infrastructure (delegates to infra/)

.PHONY: up down ps logs nuke

up: ## Start postgres + rustfs + redis
	$(MAKE) -C infra up

down: ## Stop containers (data preserved)
	$(MAKE) -C infra down

ps: ## Show container status
	$(MAKE) -C infra ps

logs: ## Tail infra logs
	$(MAKE) -C infra logs

nuke: ## Stop containers AND remove volumes (destroys local data)
	$(MAKE) -C infra nuke

##@ Database (delegates to infra/db)

.PHONY: db-up db-down db-status db-new db-dump seed-dev seed-reset

db-up: ## Apply pending migrations
	$(MAKE) -C infra db-up

db-down: ## Roll back the latest migration
	$(MAKE) -C infra db-down

db-status: ## Show applied / pending migrations
	$(MAKE) -C infra db-status

db-new: ## Create a new migration. Usage: make db-new name=add_widgets
	$(MAKE) -C infra db-new name=$(name)

db-dump: ## Refresh infra/db/schema.sql from the live DB
	$(MAKE) -C infra db-dump

seed-dev: ## Load dev seed data
	$(MAKE) -C infra seed-dev

seed-reset: ## Reset DB then load dev seeds
	$(MAKE) -C infra seed-reset

##@ Services

.PHONY: agentic agentic-install api api-build api-sqlc

agentic: ## Run the agentic service (FastAPI on :8000)
	$(MAKE) -C services/agentic run

agentic-install: ## Sync agentic Python deps
	$(MAKE) -C services/agentic install

api: ## Run the api service (Go/Fiber on :8080)
	$(MAKE) -C services/api dev

api-build: ## Build api release binary
	$(MAKE) -C services/api build

api-sqlc: ## Regenerate api Go types from infra/db/schema.sql
	$(MAKE) -C services/api sqlc

##@ Quality

.PHONY: test lint

test: ## Run tests in every service
	$(MAKE) -C services/api test

lint: ## Lint every service
	$(MAKE) -C services/api lint

##@ One-shot

.PHONY: setup bootstrap

bootstrap: ## First-time setup: infra up, migrations applied, schema dumped, sqlc regenerated
	$(MAKE) up
	$(MAKE) db-up
	$(MAKE) db-dump
	$(MAKE) api-sqlc

setup: bootstrap ## Alias for bootstrap
