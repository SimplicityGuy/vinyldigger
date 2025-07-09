# VinylDigger Testing Guide

This guide covers all testing approaches used in the VinylDigger project.

## Test Types

### 1. Backend Tests

**Unit and Integration Tests** (`backend/tests/`)
- Framework: pytest
- Coverage: API endpoints, services, models, authentication
- Database: Uses test PostgreSQL instance
- Location: `backend/tests/`

### 2. Frontend Tests

**Unit Tests** (`frontend/src/**/*.test.ts`)
- Framework: Vitest
- Coverage: Components, hooks, utilities
- Location: `frontend/tests/unit/`

**E2E Tests** (`frontend/tests/e2e/`)
- Framework: Playwright
- Coverage: Full user workflows, cross-browser testing
- Browsers: Chromium, Firefox, Safari, Mobile Safari (iPhone, iPad)
- Location: `frontend/tests/e2e/`

## Running Tests

### Quick Commands

```bash
# Run all tests (backend in Docker)
just test

# Run backend tests locally
just test-backend

# Run frontend unit tests
just test-frontend

# Run e2e tests
just test-e2e

# Run all tests locally (no Docker)
just test-local
```

### Backend Tests

#### Using Docker (Recommended)
```bash
# Run all backend tests in isolated environment
docker-compose -f docker-compose.test.yml run --rm backend-test

# Or use just command
just test-docker-backend
```

#### Local Development
```bash
# Run tests with coverage
cd backend
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/test_auth.py

# Run with verbose output
uv run pytest -v
```

### Frontend Tests

#### Unit Tests
```bash
# Run all unit tests
cd frontend
npm run test

# Run in watch mode
npm run test -- --watch

# Run with coverage
npm run test -- --coverage
```

#### E2E Tests
```bash
# Run all e2e tests (headless)
cd frontend
npm run test:e2e

# Run specific browser
npm run test:e2e -- --project=chromium
npm run test:e2e -- --project=firefox
npm run test:e2e -- --project=webkit
npm run test:e2e -- --project=mobile-safari-iphone
npm run test:e2e -- --project=mobile-safari-ipad

# Run in UI mode (interactive)
npm run test:e2e:ui

# Run specific test file
npm run test:e2e -- tests/e2e/auth.spec.ts

# Debug mode
npm run test:e2e -- --debug
```

## Test Environment

### Docker Compose Test Setup

The `docker-compose.test.yml` file provides:
- **postgres**: Test database (PostgreSQL 16)
- **redis**: Cache and message broker
- **backend**: API server for e2e tests
- **backend-test**: Test runner for backend tests
- **worker**: Celery worker for background tasks
- **frontend**: Development server for e2e tests

### Starting Test Services

```bash
# Start all test services
just test-services-up

# Check service health
docker-compose -f docker-compose.test.yml ps

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Stop services
just test-down
```

## CI/CD Integration

### GitHub Actions Workflows

1. **Main CI Workflow** (`.github/workflows/ci.yml`)
   - Runs on every push and PR
   - Executes backend and frontend unit tests
   - Runs linting and type checking

2. **E2E Test Workflow** (`.github/workflows/e2e-tests.yml`)
   - Runs comprehensive e2e tests
   - Tests all browsers in parallel
   - Uploads test artifacts (reports, videos)

### Running Tests in CI

The CI environment:
- Uses frozen dependency versions
- Runs tests in parallel where possible
- Generates coverage reports
- Uploads artifacts for debugging

## Test Data

### Backend Test Fixtures
- Located in `backend/tests/conftest.py`
- Provides database sessions, test users, mock services
- Automatically cleans up after tests

### E2E Test Helpers
- `generateTestUser()`: Creates unique test data
- `setupAuthentication()`: Mocks authenticated state
- `fillLoginForm()`: Form filling utilities

## Coverage Requirements

### Backend
- Target: 80% overall coverage
- Critical paths: 100% coverage
- Run: `cd backend && uv run pytest --cov=src --cov-report=html`
- View: Open `backend/htmlcov/index.html`

### Frontend
- Target: 70% overall coverage
- Critical components: 90% coverage
- Run: `cd frontend && npm run test -- --coverage`
- View: Open `frontend/coverage/index.html`

## Debugging Failed Tests

### Backend Tests
```bash
# Run with detailed output
uv run pytest -vv

# Run with pdb on failure
uv run pytest --pdb

# Run specific test with print output
uv run pytest -s tests/test_auth.py::test_login
```

### E2E Tests
```bash
# Run in headed mode
npm run test:e2e -- --headed

# Save trace on failure
npm run test:e2e -- --trace on

# Debug specific test
npm run test:e2e -- --debug tests/e2e/auth.spec.ts
```

### Viewing Test Reports
```bash
# Playwright HTML report
npx playwright show-report

# Backend coverage report
cd backend && python -m http.server 8080 --directory htmlcov
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Deterministic**: Use mocks for external services
3. **Fast**: Keep tests focused and fast
4. **Descriptive**: Use clear test names
5. **Comprehensive**: Test happy paths and edge cases

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000, 5432, 6379, 8000 are free
2. **Docker issues**: Run `just clean` to reset
3. **Dependency issues**: Run `just install` to reinstall
4. **Database issues**: Check migrations with `just migrate`

### Reset Test Environment
```bash
# Stop all services and clean up
just test-down
just clean

# Reinstall dependencies
just install

# Start fresh
just test-services-up
```
