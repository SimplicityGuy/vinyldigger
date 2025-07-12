# VinylDigger Testing Guide

## Overview

This guide covers testing strategies, patterns, and best practices for the VinylDigger project. We use pytest for backend testing and Vitest for frontend testing, with comprehensive mocking strategies to ensure fast, reliable tests.

## Running Tests

### Quick Commands

```bash
# Run all tests in Docker (recommended for CI-like environment)
just test

# Run tests locally (faster for development)
just test-local

# Run backend tests only
just test-backend

# Run frontend tests only
just test-frontend

# Run specific backend test file
cd backend && uv run pytest tests/test_api_auth.py -v

# Run specific frontend test
cd frontend && npm test src/services/__tests__/api.test.ts
```

### Pre-Test Checklist

1. **Run lint checks first**: `just lint` - This catches issues before they cause test failures
2. **Ensure database is running**: `just up postgres redis` for local tests
3. **Check environment variables**: Tests use `.env.test` configurations

## Backend Testing

### Test Structure

```
backend/tests/
├── conftest.py          # Shared fixtures and configuration
├── test_api_*.py        # API endpoint tests
├── test_services_*.py   # Service layer tests
├── test_models_*.py     # Model tests
└── test_workers_*.py    # Background task tests
```

### Common Test Patterns

#### 1. Database Testing with Fixtures

```python
import pytest
from sqlalchemy.orm import Session
from src.models.user import User

def test_create_user(db: Session):
    """Test creating a user in the database."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash="hashed"
    )
    db.add(user)
    db.commit()

    assert user.id is not None
    assert user.email == "test@example.com"
```

#### 2. API Endpoint Testing

```python
from fastapi.testclient import TestClient

def test_login_success(client: TestClient, db: Session):
    """Test successful login."""
    # Create test user first
    user = create_test_user(db)

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
```

#### 3. Mocking External APIs

```python
from unittest.mock import patch, MagicMock

@patch("src.services.discogs.requests.get")
def test_discogs_search(mock_get: MagicMock, db: Session):
    """Test Discogs API search with mocked response."""
    # Setup mock response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "results": [
            {
                "id": 123,
                "title": "Test Album",
                "year": "2023",
                "format": ["Vinyl", "LP"]
            }
        ]
    }

    # Test the service
    service = DiscogsService()
    results = service.search("Test Album")

    assert len(results) == 1
    assert results[0]["title"] == "Test Album"
    mock_get.assert_called_once()
```

### Backend Testing Best Practices

1. **Use pytest fixtures** for common test data and database sessions
2. **Mock all external services** - Never make real API calls
3. **Test both success and error cases** - Include edge cases
4. **Use meaningful test names** - `test_login_with_invalid_credentials` not `test_login_2`
5. **Keep tests isolated** - Each test should work independently
6. **Platform name consistency** - Always use lowercase (e.g., `platform="discogs"`)

## Frontend Testing

### Test Structure

```
frontend/src/
├── components/__tests__/    # Component tests
├── hooks/__tests__/         # Custom hook tests
├── services/__tests__/      # API service tests
└── lib/__tests__/          # Utility tests
```

### Common Test Patterns

#### 1. Component Testing

```typescript
import { render, screen } from '@testing-library/react';
import { SearchForm } from '../SearchForm';

describe('SearchForm', () => {
  it('renders search input and button', () => {
    render(<SearchForm onSubmit={vi.fn()} />);

    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument();
  });

  it('calls onSubmit with search query', async () => {
    const handleSubmit = vi.fn();
    const { user } = render(<SearchForm onSubmit={handleSubmit} />);

    const input = screen.getByPlaceholderText(/search/i);
    await user.type(input, 'Pink Floyd');
    await user.click(screen.getByRole('button', { name: /search/i }));

    expect(handleSubmit).toHaveBeenCalledWith({ query: 'Pink Floyd' });
  });
});
```

#### 2. API Service Testing

```typescript
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { api } from '../api';

// Mock fetch globally
global.fetch = vi.fn();

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Setup localStorage mock for auth tokens
    const localStorageMock = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    };
    global.localStorage = localStorageMock as any;
  });

  it('includes auth token in requests', async () => {
    const mockToken = 'test-token';
    (localStorage.getItem as any).mockReturnValue(mockToken);

    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: 'test' })
    });

    await api.get('/test');

    expect(fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': `Bearer ${mockToken}`
        })
      })
    );
  });
});
```

#### 3. Mock Factories

```typescript
// tests/factories/search.ts
import { SavedSearch, SearchResult } from '@/types';

export const createMockSearch = (overrides?: Partial<SavedSearch>): SavedSearch => ({
  id: '1',
  name: 'Test Search',
  query: 'pink floyd',
  platform: 'discogs',  // Always use lowercase!
  min_price: 10,
  max_price: 100,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides
});

export const createMockSearchResult = (overrides?: Partial<SearchResult>): SearchResult => ({
  id: '1',
  search_id: '1',
  platform: 'discogs',
  title: 'The Dark Side of the Moon',
  artist: 'Pink Floyd',
  price: 25.99,
  currency: 'USD',
  url: 'https://www.discogs.com/...',
  ...overrides
});
```

### Frontend Testing Best Practices

1. **TypeScript type safety** - Ensure mocks match actual types
2. **Use Testing Library queries** - Prefer `getByRole` over `getByTestId`
3. **Mock at the right level** - Mock fetch/API calls, not internal functions
4. **Test user interactions** - Use `userEvent` for realistic interactions
5. **Avoid implementation details** - Test behavior, not component internals
6. **Reuse mock factories** - Create consistent test data generators

## Mock Setup Patterns

### Backend Mock Patterns

```python
# conftest.py - Reusable mocks
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_discogs_api():
    """Mock Discogs API responses."""
    with patch("src.services.discogs.requests") as mock:
        mock.get.return_value.status_code = 200
        mock.get.return_value.json.return_value = {
            "results": []
        }
        yield mock

@pytest.fixture
def mock_redis():
    """Mock Redis for testing without actual Redis."""
    with patch("src.core.cache.redis_client") as mock:
        mock.get.return_value = None
        mock.set.return_value = True
        yield mock
```

### Frontend Mock Patterns

```typescript
// tests/setup.ts - Global test setup
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// Mock window.localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock as any;

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
})) as any;
```

## Common Testing Pitfalls

### 1. Platform Name Consistency
```python
# ❌ Wrong - inconsistent casing
search = SavedSearch(platform="Discogs")  # or "DISCOGS"

# ✅ Correct - always lowercase in code
search = SavedSearch(platform="discogs")
```

### 2. Forgetting to Mock External Services
```python
# ❌ Wrong - makes real API call
def test_search():
    service = DiscogsService()
    results = service.search("test")  # This will hit real API!

# ✅ Correct - mock the external call
@patch("requests.get")
def test_search(mock_get):
    mock_get.return_value.json.return_value = {"results": []}
    service = DiscogsService()
    results = service.search("test")
```

### 3. Not Running Lint Before Tests
```bash
# ❌ Wrong - test might fail due to lint issues
just test

# ✅ Correct - catch issues early
just lint && just test
```

### 4. Database State Between Tests
```python
# ❌ Wrong - tests depend on order
def test_create_user(db):
    create_user(db, "test@example.com")

def test_duplicate_user(db):
    # This fails if test_create_user didn't run first!
    with pytest.raises(IntegrityError):
        create_user(db, "test@example.com")

# ✅ Correct - each test is independent
def test_duplicate_user(db):
    create_user(db, "test@example.com")
    with pytest.raises(IntegrityError):
        create_user(db, "test@example.com")
```

## Debugging Test Failures

### Backend Debugging

```bash
# Run with verbose output
cd backend && uv run pytest -v

# Run with print statements visible
cd backend && uv run pytest -s

# Run specific test with debugging
cd backend && uv run pytest tests/test_api_auth.py::test_login -vvs

# Check test coverage
cd backend && uv run pytest --cov=src --cov-report=html
```

### Frontend Debugging

```bash
# Run in watch mode
cd frontend && npm test -- --watch

# Run with coverage
cd frontend && npm test -- --coverage

# Debug in browser
cd frontend && npm test -- --ui
```

## CI/CD Testing

Our GitHub Actions workflow runs tests in a controlled environment:

1. **Backend tests** run in Docker with PostgreSQL and Redis
2. **Frontend tests** run with mocked APIs
3. **Lint checks** run before tests to catch issues early
4. **Coverage reports** are generated for monitoring

### Local CI Simulation

```bash
# Run tests like CI does
just test

# Or manually:
docker-compose -f docker-compose.yml -f docker-compose.test.yml up --exit-code-from test
```

## Test Data Management

### Backend Test Data

```python
# tests/factories.py
from src.models.user import User
from src.models.search import SavedSearch

def create_test_user(db, **kwargs):
    """Create a test user with defaults."""
    defaults = {
        "email": "test@example.com",
        "username": "testuser",
        "password_hash": "hashed"
    }
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    db.commit()
    return user

def create_test_search(db, user, **kwargs):
    """Create a test search with defaults."""
    defaults = {
        "name": "Test Search",
        "query": "pink floyd",
        "platform": "discogs",  # Always lowercase!
        "user_id": user.id
    }
    defaults.update(kwargs)
    search = SavedSearch(**defaults)
    db.add(search)
    db.commit()
    return search
```

### Frontend Test Data

```typescript
// tests/utils/testData.ts
export const testUser = {
  id: '1',
  username: 'testuser',
  email: 'test@example.com'
};

export const testSearch = {
  id: '1',
  name: 'Pink Floyd Search',
  query: 'pink floyd',
  platform: 'discogs' as const,  // TypeScript const assertion
  min_price: 10,
  max_price: 100
};
```

## Summary

Effective testing in VinylDigger requires:

1. **Consistent practices** - Always lint before testing, use lowercase platform names
2. **Proper mocking** - Mock all external dependencies
3. **Type safety** - Ensure TypeScript types match in frontend tests
4. **Isolation** - Each test should be independent
5. **Meaningful data** - Use realistic test data that matches production

Remember: Good tests are an investment in code quality and developer confidence. They should be easy to write, fast to run, and clear about what they're testing.
