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
