# ─────────────────────────────────────────────────────────────────────────────
# api — Go/Fiber REST service. Connects to the Postgres started by ../../infra.
# Migrations and schema (sqlc input) live in ../../infra/db (not here).
# ─────────────────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<target>\033[0m\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ App

.PHONY: dev build

dev: ## Run the HTTP server (go run ./cmd/http)
	go run ./cmd/http

build: ## Build a release binary into ./bin/http
	go build -o bin/http ./cmd/http

##@ Tests & quality

.PHONY: test test-integration race lint fmt

test: ## Run unit tests
	go test ./...

test-integration: ## Run integration tests (build tag: integration)
	go test -tags=integration ./...

race: ## Run tests with the race detector
	go test -race ./...

lint: ## go vet ./...
	go vet ./...

fmt: ## gofmt -w ./cmd ./internal
	gofmt -w ./cmd ./internal

##@ Code generation

.PHONY: sqlc

sqlc: ## Regenerate internal/repository from ../../infra/db/schema.sql
	sqlc generate

##@ Infrastructure (delegates to ../../infra)

.PHONY: infra-up infra-down infra-ps infra-logs graph-up graph-down

infra-up: ## Start shared infra (postgres + rustfs + redis)
	$(MAKE) -C ../../infra up

infra-down: ## Stop shared infra
	$(MAKE) -C ../../infra down

infra-ps: ## Show container status
	$(MAKE) -C ../../infra ps

infra-logs: ## Tail infra logs
	$(MAKE) -C ../../infra logs

graph-up: ## Start optional Neo4j (graph profile)
	$(MAKE) -C ../../infra graph-up

graph-down: ## Stop Neo4j
	$(MAKE) -C ../../infra graph-down

##@ Database (delegates to ../../infra/db)

.PHONY: db-up db-down db-status db-new db-dump

db-up: ## Apply pending migrations
	$(MAKE) -C ../../infra db-up

db-down: ## Roll back the latest migration
	$(MAKE) -C ../../infra db-down

db-status: ## Show applied / pending migrations
	$(MAKE) -C ../../infra db-status

db-new: ## Create a new migration. Usage: make db-new name=add_widgets
	$(MAKE) -C ../../infra db-new name=$(name)

db-dump: ## Refresh ../../infra/db/schema.sql from the live DB
	$(MAKE) -C ../../infra db-dump

##@ Seeds (delegates to ../../infra/db/seeds)

.PHONY: seed-dev seed-reset

seed-dev: ## Load dev seed data
	$(MAKE) -C ../../infra seed-dev

seed-reset: ## Reset DB then load dev seeds
	$(MAKE) -C ../../infra seed-reset

##@ One-shot

.PHONY: setup

setup: infra-up db-up sqlc dev ## Start infra, apply migrations, regen sqlc, run app
