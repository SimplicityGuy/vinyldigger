.PHONY: help build up down logs ps test clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

ps: ## Show running services
	docker-compose ps

test: ## Run all tests
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from backend

clean: ## Clean up containers, volumes, and images
	docker-compose down -v
	docker system prune -f

migrate: ## Run database migrations
	docker-compose exec backend alembic upgrade head

shell-backend: ## Open a shell in the backend container
	docker-compose exec backend /bin/sh

shell-db: ## Open a PostgreSQL shell
	docker-compose exec postgres psql -U postgres vinyldigger

install-pre-commit: ## Install pre-commit hooks
	pre-commit install