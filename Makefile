# ============================================================
#  AI Support Ticket Triage System — Makefile
# ============================================================

.PHONY: help dev build up down logs test lint format migrate seed clean

# ── Variables ────────────────────────────────────────────────
DC := docker compose
BACKEND := $(DC) exec backend
WORKER := $(DC) exec worker

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Docker ───────────────────────────────────────────────────
build: ## Build all containers
	$(DC) build

up: network ## Start all services
	$(DC) up -d

down: ## Stop all services
	$(DC) down

# ── Infrastructure Monitoring ────────────────────────────────
network: ## Create shared docker network for infra
	docker network create support_network || true

infra-up: network ## Start monitoring infrastructure
	$(DC) -f infra/docker-compose.yml up -d

infra-down: ## Stop monitoring infrastructure
	$(DC) -f infra/docker-compose.yml down

dev: network ## Start in development mode with logs
	$(DC) up --build

logs: ## Tail logs for all services
	$(DC) logs -f

logs-backend: ## Tail backend logs
	$(DC) logs -f backend

logs-worker: ## Tail worker logs
	$(DC) logs -f worker

restart: ## Restart all services
	$(DC) restart

ps: ## Show running services
	$(DC) ps

# ── Database ─────────────────────────────────────────────────
migrate: ## Run database migrations
	$(BACKEND) alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	$(BACKEND) alembic revision --autogenerate -m "$(MSG)"

migrate-downgrade: ## Downgrade one migration
	$(BACKEND) alembic downgrade -1

seed: ## Seed database with sample data
	$(BACKEND) python -m app.seed

db-reset: ## Reset database (dangerous!)
	$(BACKEND) alembic downgrade base
	$(BACKEND) alembic upgrade head
	$(BACKEND) python -m app.seed

# ── Testing ──────────────────────────────────────────────────
test: ## Run all tests
	@make test-backend
	@make test-frontend

test-backend: ## Run backend tests
	$(BACKEND) pytest -v --cov=app --cov-report=term-missing

test-frontend: ## Run frontend tests
	$(DC) exec frontend npm run test

# ── Linting & Formatting ────────────────────────────────────
lint: ## Run all linters
	@make lint-backend
	@make lint-frontend

lint-backend: ## Lint backend code
	$(BACKEND) ruff check app/
	$(BACKEND) mypy app/

lint-frontend: ## Lint frontend code
	$(DC) exec frontend npm run lint

format: ## Format all code
	@make format-backend
	@make format-frontend

format-backend: ## Format backend code
	$(BACKEND) ruff format app/
	$(BACKEND) ruff check --fix app/

format-frontend: ## Format frontend code
	$(DC) exec frontend npm run format

# ── Utilities ────────────────────────────────────────────────
shell-backend: ## Open shell in backend container
	$(BACKEND) bash

shell-db: ## Open psql shell
	$(DC) exec postgres psql -U support_user -d support_triage

redis-cli: ## Open Redis CLI
	$(DC) exec redis redis-cli

clean: ## Remove all containers, volumes, and images
	$(DC) down -v --rmi all --remove-orphans

install-backend: ## Install backend dependencies locally
	cd backend && pip install -e ".[dev]"

install-frontend: ## Install frontend dependencies locally
	cd frontend && npm install
