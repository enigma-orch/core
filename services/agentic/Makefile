# ─────────────────────────────────────────────────────────────────────────────
# agentic — FastAPI service. Connects to the Postgres + RustFS started by
# ../infra. Migrations and schema live in ../infra/db (not here).
# ─────────────────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<target>\033[0m\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ App

.PHONY: install run

install: ## Sync Python deps with uv
	uv sync --all-groups

run: ## Start FastAPI on :8000 with reload
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

##@ Infrastructure (delegates to ../infra)

.PHONY: infra-up infra-down infra-ps infra-logs

infra-up: ## Start shared infra (postgres + rustfs + redis)
	$(MAKE) -C ../infra up

infra-down: ## Stop shared infra
	$(MAKE) -C ../infra down

infra-ps: ## Show container status
	$(MAKE) -C ../infra ps

infra-logs: ## Tail infra logs
	$(MAKE) -C ../infra logs

##@ Database (delegates to ../infra/db)

.PHONY: migrate db-status db-new

migrate: ## Apply pending migrations
	$(MAKE) -C ../infra db-up

db-status: ## Show applied / pending migrations
	$(MAKE) -C ../infra db-status

db-new: ## Create a new migration. Usage: make db-new name=add_widgets
	$(MAKE) -C ../infra db-new name=$(name)

##@ One-shot

.PHONY: setup

setup: infra-up migrate run ## Start infra, run migrations, start app
