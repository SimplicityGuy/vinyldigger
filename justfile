# Show available commands
default:
    @just --list

# Build all Docker images
build:
    docker-compose build

# Start all services
up:
    docker-compose up -d

# Stop all services
down:
    docker-compose down

# Show logs from all services
logs:
    docker-compose logs -f

# Show running services
ps:
    docker-compose ps

# Run all tests
test:
    docker-compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from backend

# Run tests in CI environment
test-ci:
    docker-compose -f docker-compose.test.yml up -d
    docker-compose -f docker-compose.test.yml ps

# Stop test services
test-down:
    docker-compose -f docker-compose.test.yml down -v

# Clean up containers, volumes, and images
clean:
    docker-compose down -v
    docker system prune -f

# Run database migrations
migrate:
    docker-compose exec backend alembic upgrade head

# Open a shell in the backend container
shell-backend:
    docker-compose exec backend /bin/sh

# Open a PostgreSQL shell
shell-db:
    docker-compose exec postgres psql -U postgres vinyldigger

# Install pre-commit hooks
install-pre-commit:
    pre-commit install

# Run pre-commit on all files
lint:
    pre-commit run --all-files

# Update and freeze pre-commit hooks
update-pre-commit:
    pre-commit autoupdate --freeze

# Run backend tests locally
test-backend:
    cd backend && uv run pytest

# Run backend tests in CI with coverage
test-backend-ci:
    cd backend && pytest --cov=src --cov-report=xml

# Run frontend tests locally
test-frontend:
    cd frontend && npm run test

# Run frontend tests in CI
test-frontend-ci:
    cd frontend && npm run test:ci

# Build frontend
build-frontend:
    cd frontend && npm run build

# Run all tests locally
test-local: test-backend test-frontend

# Install backend dependencies
install-backend:
    cd backend && uv sync --dev

# Install backend dependencies for CI (system install)
install-backend-ci:
    cd backend && uv pip install -e ".[dev]" --system

# Install frontend dependencies
install-frontend:
    cd frontend && npm ci

# Install all dependencies
install: install-backend install-frontend install-pre-commit

# Run backend development server
dev-backend:
    cd backend && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend development server
dev-frontend:
    cd frontend && npm run dev

# Format code
format:
    cd backend && uv run ruff format .
    cd frontend && npm run format

# Type check
typecheck:
    cd backend && uv run mypy .
    cd frontend && npm run typecheck
