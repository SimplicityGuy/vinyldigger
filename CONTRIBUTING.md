# Contributing to VinylDigger

Thank you for your interest in contributing to VinylDigger! This document provides guidelines and instructions for contributing to the project.

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Git
- Just (recommended) - Install from https://github.com/casey/just
- For local development:
  - Python 3.13 with uv - Install from https://github.com/astral-sh/uv
  - Node.js 22+ with npm

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/vinyldigger.git
   cd vinyldigger
   ```

2. **Install dependencies and pre-commit hooks**
   ```bash
   just install
   # This installs backend deps, frontend deps, and pre-commit hooks
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start services**
   ```bash
   just up
   ```

5. **Verify setup**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs

## 📝 Development Workflow

### Essential Rules
1. **Always use uv** for Python package management - never use pip directly
2. **Use the justfile** for common commands
3. **Run pre-commit checks** before committing: `just lint`
4. **Write tests** for new features and bug fixes
5. **Update documentation** when changing functionality

### Code Style

#### Python (Backend)
- Follow PEP 8, enforced by Ruff
- Use type hints for all functions
- Write docstrings for public functions and classes
- Maximum line length: 120 characters

#### TypeScript (Frontend)
- Follow the ESLint v9 configuration
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use proper TypeScript types (avoid `any`)

#### Commit Messages
- Use conventional commits format:
  ```
  type(scope): description

  [optional body]

  [optional footer]
  ```
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Examples:
  - `feat(api): add vinyl condition filter`
  - `fix(auth): resolve token refresh issue`
  - `docs: update installation instructions`

### Pre-commit Checks

Before committing, ensure all checks pass:
```bash
# Run all pre-commit checks
just lint

# Auto-fix issues where possible
just format
```

Pre-commit will check:
- Code formatting (Ruff for Python, Prettier for JS/TS)
- Linting (Ruff for Python, ESLint for TypeScript)
- Type checking (mypy for Python, TypeScript compiler)
- YAML/JSON syntax
- No large files
- No merge conflicts

## 🧪 Testing

### Running Tests

```bash
# All tests in Docker
just test

# Local tests
just test-local

# Backend tests only
just test-backend

# Frontend tests only
just test-frontend

# E2E tests
cd frontend && npm run test:e2e
```

### Writing Tests

#### Backend Tests
- Use pytest for all tests
- Place tests in `backend/tests/`
- Use fixtures for common test data
- Mock external API calls
- Aim for >80% code coverage

Example:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_search(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/searches",
        json={"name": "Test Search", "query": "vinyl"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Search"
```

#### Frontend Tests
- Use Vitest for unit tests
- Use Testing Library for component tests
- Place tests next to components or in `__tests__` folders
- Mock API calls and external dependencies

Example:
```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { SearchForm } from './SearchForm'

describe('SearchForm', () => {
  it('renders search input', () => {
    render(<SearchForm onSubmit={() => {}} />)
    expect(screen.getByPlaceholderText('Search for vinyl...')).toBeInTheDocument()
  })
})
```

## 🔄 Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Add tests for new functionality
   - Update documentation as needed

3. **Ensure quality**
   ```bash
   # Run linting
   just lint

   # Run tests
   just test-local
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing new feature"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Use a clear, descriptive title
   - Reference any related issues
   - Describe what changes were made and why
   - Include screenshots for UI changes

### PR Requirements
- All CI checks must pass
- Code review approval required
- No merge conflicts
- Up-to-date with main branch

## 🏗️ Project Structure

### Backend (`/backend`)
```
src/
├── api/v1/       # API endpoints
├── core/         # Core utilities
├── models/       # SQLAlchemy models
├── services/     # Business logic
└── workers/      # Background tasks
```

### Frontend (`/frontend`)
```
src/
├── components/   # Reusable UI components
├── pages/        # Route components
├── hooks/        # Custom React hooks
├── lib/          # Utilities
└── services/     # API integration
```

## 🛠️ Common Tasks

### Adding a New API Endpoint
1. Create endpoint in `backend/src/api/v1/endpoints/`
2. Add Pydantic schemas for request/response
3. Include in router
4. Add tests in `backend/tests/`
5. Update API client in frontend

### Adding a New UI Component
1. Create component in `frontend/src/components/`
2. Use TypeScript and proper types
3. Add unit tests
4. Use Tailwind CSS v4 for styling
5. Document props with JSDoc comments

### Updating Dependencies

#### Python Dependencies
```bash
cd backend
# Add a dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Update all dependencies
uv sync
```

#### JavaScript Dependencies
```bash
cd frontend
# Add a dependency
npm install package-name

# Add a dev dependency
npm install -D package-name

# Update dependencies
npm update
```

### Database Migrations
```bash
# Create a new migration
cd backend
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
just migrate
```

## 🐛 Reporting Issues

### Bug Reports
Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, browser, etc.)
- Error messages or logs
- Screenshots if applicable

### Feature Requests
Include:
- Clear description of the feature
- Use case and benefits
- Proposed implementation (optional)
- Mockups or examples (optional)

## 💡 Getting Help

- Check existing issues and PRs
- Review the API documentation
- Ask questions in issues
- Refer to CLAUDE.md for detailed technical context

## 📜 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing opinions
- Report unacceptable behavior to project maintainers

## 🙏 Recognition

Contributors will be recognized in:
- The project README
- Release notes
- Special thanks section

Thank you for contributing to VinylDigger!
