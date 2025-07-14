# VinylDigger Testing Strategy

Comprehensive testing guide for the VinylDigger project, covering backend (pytest), frontend (Vitest), and E2E (Playwright) testing approaches.

## Quick Start

### Essential Commands
```bash
# ALWAYS run lint checks first - catches issues before they cause test failures
just lint

# Run all tests in Docker (CI-like environment)
just test

# Run tests locally (faster for development)
just test-local

# Run specific test suites
just test-backend     # Backend only
just test-frontend    # Frontend only
just test-e2e        # E2E tests
```

## Test Architecture

### Backend Tests (`backend/tests/`)
- **Framework**: pytest with async support
- **Database**: PostgreSQL test instance with transactions
- **Mocking**: External APIs (Discogs, eBay) fully mocked
- **Coverage Target**: 80% overall, 100% for critical paths

### Frontend Tests
- **Unit Tests**: Vitest with Testing Library
- **E2E Tests**: Playwright with multi-browser support
- **Mocking**: API calls mocked at fetch level
- **Coverage Target**: 70% overall, 90% for critical components

### Analysis Engine Tests
- **Item Matching**: Fuzzy matching and deduplication algorithms
- **Seller Analysis**: Reputation scoring and shipping optimization
- **Recommendations**: Multi-item deal identification
- **Performance**: Large dataset handling (<30s for 1000 items)

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

**Automatic Setup (Recommended)**
```bash
# From frontend directory - automatically starts backend services
npm run test:e2e

# Keep services running after tests
KEEP_SERVICES_RUNNING=1 npm run test:e2e

# Skip automatic Docker setup (if services already running)
SKIP_DOCKER_SETUP=1 npm run test:e2e
```

**Using Just Commands**
```bash
# Run with explicit service management
just test-e2e

# Run with automatic service management
just test-e2e-local

# Run in UI mode
just test-e2e-ui
```

**Advanced Options**
```bash
# Run specific browser
npm run test:e2e -- --project=chromium
npm run test:e2e -- --project=firefox
npm run test:e2e -- --project=webkit

# Run in UI mode (interactive)
npm run test:e2e:ui

# Run with visible browser
npm run test:e2e:headed

# Run specific test file
npm run test:e2e -- tests/e2e/auth.spec.ts

# Debug mode
npm run test:e2e:debug

# Generate new tests with codegen
npm run test:e2e:codegen
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

## Critical Testing Rules

### 1. Pre-Test Checklist
- **Run `just lint` first**: Catches type, format, and style issues early
- **Check environment**: Ensure PostgreSQL and Redis are running for local tests
- **Verify mocks**: All external API calls must be mocked

### 2. Platform Name Consistency
```python
# ✅ CORRECT - Always use lowercase in backend code
search = SavedSearch(platform="discogs")
result = SearchResult(platform="ebay")

# ❌ WRONG - Will cause test failures
search = SavedSearch(platform="Discogs")  # or "DISCOGS"
```

### 3. UUID Handling in Tests
```python
# ✅ CORRECT - Use UUID objects in fixtures
from uuid import uuid4
user_id = uuid4()  # UUID object

# ❌ WRONG - Don't use string UUIDs
user_id = str(uuid4())  # String
```

### 4. Async Testing Patterns
```python
# ✅ CORRECT - Use AsyncMock for async operations
from unittest.mock import AsyncMock
mock_db = AsyncMock(spec=AsyncSession)
mock_db.execute = AsyncMock()

# ❌ WRONG - Regular Mock won't work for async
mock_db = Mock()  # Will fail for async operations
```

## Best Practices

### Backend Testing
1. **Use pytest fixtures** for common test data and database sessions
2. **Mock all external services** - Never make real API calls
3. **Test both success and error cases** - Include edge cases
4. **Keep tests isolated** - Each test should work independently
5. **Use meaningful test names** - `test_login_with_invalid_credentials` not `test_login_2`

### Frontend Testing
1. **TypeScript type safety** - Ensure mocks match actual types
2. **Use Testing Library queries** - Prefer `getByRole` over `getByTestId`
3. **Mock at the right level** - Mock fetch/API calls, not internal functions
4. **Test user interactions** - Use `userEvent` for realistic interactions
5. **Reuse mock factories** - Create consistent test data generators

### Analysis Engine Testing
1. **Use realistic test data** - Mirror actual API responses
2. **Test scoring edge cases** - Zero feedback, missing data, extreme values
3. **Verify recommendation ranking** - Ensure proper sorting
4. **Test cross-platform scenarios** - Mix Discogs and eBay results
5. **Validate performance** - Large datasets should process efficiently

## Common Testing Pitfalls & Solutions

### 1. Import/Type Errors
**Problem**: `ModuleNotFoundError` or `TypeError` in tests
**Solution**:
```bash
just lint  # Run type checking first
cd backend && uv sync  # Ensure dependencies are installed
```

### 2. Database State Issues
**Problem**: Tests fail when run in different order
**Solution**: Ensure each test is independent
```python
# ✅ Each test creates its own data
def test_duplicate_user(db):
    create_user(db, "test@example.com")
    with pytest.raises(IntegrityError):
        create_user(db, "test@example.com")
```

### 3. Mock Configuration Errors
**Problem**: Tests making real API calls
**Solution**: Properly patch at the import location
```python
# ✅ Patch where it's imported, not where it's defined
@patch("src.services.discogs.requests.get")
def test_search(mock_get):
    # mock configuration
```

### 4. Async Test Failures
**Problem**: `RuntimeWarning: coroutine was never awaited`
**Solution**: Use proper async test patterns
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

### 5. Frontend Type Mismatches
**Problem**: TypeScript errors in test mocks
**Solution**: Use mock factories with proper types
```typescript
// Create typed mock factories
export const createMockSearch = (overrides?: Partial<SavedSearch>): SavedSearch => ({
  // ... default values with correct types
  ...overrides
});
```

## Debugging Test Failures

### Backend Debugging
```bash
# Verbose output with print statements
cd backend && uv run pytest -vvs

# Run specific test with debugging
cd backend && uv run pytest tests/test_api_auth.py::test_login -vvs --pdb

# Check test coverage gaps
cd backend && uv run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Frontend Debugging
```bash
# Interactive UI mode
cd frontend && npm test -- --ui

# Run specific test file
cd frontend && npm test src/services/__tests__/api.test.ts

# Debug in watch mode
cd frontend && npm test -- --watch
```

### E2E Debugging
```bash
# Run with visible browser
npm run test:e2e -- --headed

# Save trace for debugging
npm run test:e2e -- --trace on

# Debug specific test
npm run test:e2e -- --debug tests/e2e/auth.spec.ts

# View test report
npx playwright show-report
```

## Test Environment Reset

### Complete Reset
```bash
# 1. Stop everything and clean volumes
just down
just clean

# 2. Reinstall all dependencies
just install

# 3. Start fresh test environment
just test-services-up

# 4. Run tests
just test
```

### Quick Reset (Keep Dependencies)
```bash
# Just restart services
just test-down
just test-services-up
```
