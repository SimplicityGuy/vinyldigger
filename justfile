# Show available commands
default:
    @just --list

# Docker Compose command detection - prefer docker-compose, fallback to docker compose
docker_compose := if `which docker-compose >/dev/null 2>&1; echo $?` == "0" { "docker-compose" } else { "docker compose" }

# Build all Docker images with OCI labels
build:
    ./scripts/docker-build.sh

# Build a specific Docker image with OCI labels (e.g., just build-service backend)
build-service service:
    ./scripts/docker-build.sh {{service}}

# Start all services
up:
    {{docker_compose}} up -d

# Stop all services
down:
    {{docker_compose}} down

# Show logs from all services
logs:
    {{docker_compose}} logs -f

# Show running services
ps:
    {{docker_compose}} ps

# Run all tests
test:
    {{docker_compose}} -f docker-compose.test.yml run --rm backend-test

# Run backend tests in Docker
test-docker-backend:
    {{docker_compose}} -f docker-compose.test.yml run --rm backend-test

# Run e2e tests (starts all services)
test-e2e:
    {{docker_compose}} -f docker-compose.test.yml up -d
    cd frontend && npm run test:e2e
    {{docker_compose}} -f docker-compose.test.yml down -v

# Run e2e tests locally with automatic service management
test-e2e-local:
    cd frontend && npm run test:e2e

# Run e2e tests in UI mode for debugging
test-e2e-ui:
    cd frontend && npm run test:e2e:ui

# Start test services for manual testing
test-services-up:
    {{docker_compose}} -f docker-compose.test.yml up -d

# Run tests in CI environment
test-ci:
    {{docker_compose}} -f docker-compose.test.yml up -d
    @echo "Waiting for services to be healthy..."
    @# Wait for PostgreSQL
    @timeout 120 bash -c 'until {{docker_compose}} -f docker-compose.test.yml exec -T postgres pg_isready -U test; do sleep 2; echo "Waiting for postgres..."; done'
    @echo "✓ PostgreSQL is ready"
    @# Wait for Redis
    @timeout 120 bash -c 'until {{docker_compose}} -f docker-compose.test.yml exec -T redis redis-cli ping | grep -q PONG; do sleep 2; echo "Waiting for redis..."; done'
    @echo "✓ Redis is ready"
    @# Wait for backend
    @timeout 180 bash -c 'until curl -f http://localhost:8000/health 2>/dev/null; do sleep 2; echo "Waiting for backend..."; done'
    @echo "✓ Backend API is ready"
    @# Wait for frontend
    @timeout 180 bash -c 'until curl -f http://localhost:3000 2>/dev/null; do sleep 2; echo "Waiting for frontend..."; done'
    @echo "✓ Frontend is ready"
    @# Wait for worker
    @timeout 120 bash -c 'until {{docker_compose}} -f docker-compose.test.yml exec -T worker celery -A src.workers.celery_app inspect ping 2>/dev/null; do sleep 2; echo "Waiting for worker..."; done'
    @echo "✓ Worker is ready"
    @echo "All services are healthy!"
    @# Give services a moment to stabilize
    @sleep 5
    {{docker_compose}} -f docker-compose.test.yml ps

# Stop test services
test-down:
    {{docker_compose}} -f docker-compose.test.yml down -v

# Wait for test services to be ready (for CI)
test-wait:
    @echo "Waiting for PostgreSQL..."
    @timeout 120 bash -c 'until {{docker_compose}} -f docker-compose.test.yml exec -T postgres pg_isready -U postgres; do echo "PostgreSQL not ready, waiting..."; sleep 2; done'
    @echo "✓ PostgreSQL is ready"
    @echo "Waiting for Redis..."
    @timeout 120 bash -c 'until {{docker_compose}} -f docker-compose.test.yml exec -T redis redis-cli ping; do echo "Redis not ready, waiting..."; sleep 2; done'
    @echo "✓ Redis is ready"
    @echo "Waiting for backend API..."
    @timeout 180 bash -c 'until curl -f http://localhost:8000/health 2>/dev/null; do echo "Backend not ready, waiting..."; sleep 2; done'
    @echo "✓ Backend API is ready"
    @echo "Waiting for frontend..."
    @timeout 180 bash -c 'until curl -f http://localhost:3000 2>/dev/null; do echo "Frontend not ready, waiting..."; sleep 2; done'
    @echo "✓ Frontend is ready"
    @echo "All services are healthy!"
    @sleep 5
    {{docker_compose}} -f docker-compose.test.yml ps

# Clean up all temporary build artifacts and caches
clean: clean-docker clean-python clean-frontend clean-misc

# Clean up Docker containers, volumes, and images
clean-docker:
    {{docker_compose}} down -v
    docker system prune -f

# Clean up Python build artifacts and caches
clean-python:
    find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find backend -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find backend -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find backend -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    find backend -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find backend -type f -name "*.pyc" -delete 2>/dev/null || true
    find backend -type f -name "*.pyo" -delete 2>/dev/null || true
    find backend -type f -name ".coverage" -delete 2>/dev/null || true
    find backend -type f -name "coverage.xml" -delete 2>/dev/null || true

# Clean up frontend build artifacts and caches
clean-frontend:
    rm -rf frontend/node_modules
    rm -rf frontend/dist
    rm -rf frontend/.vite
    rm -rf frontend/build
    rm -rf frontend/.next
    rm -rf frontend/playwright-report
    rm -rf frontend/test-results
    rm -rf frontend/coverage

# Clean up miscellaneous files
clean-misc:
    find . -type f -name ".DS_Store" -delete 2>/dev/null || true
    find . -type f -name "*.log" -delete 2>/dev/null || true
    find . -type d -name ".tmp" -exec rm -rf {} + 2>/dev/null || true

# Run database migrations
migrate:
    {{docker_compose}} exec backend uv run alembic upgrade head

# Open a shell in the backend container
shell-backend:
    {{docker_compose}} exec backend /bin/sh

# Open a PostgreSQL shell
shell-db:
    {{docker_compose}} exec postgres psql -U postgres vinyldigger

# Install pre-commit hooks
install-pre-commit:
    pip install pre-commit
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
    cd backend && uv run pytest --cov=src --cov-report=xml

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
