# Contributing to VinylDigger

## Development Setup

1. Clone the repository
2. Install pre-commit hooks: `just install-pre-commit`
3. Copy `.env.example` to `.env`
4. Start services: `just up`

## Code Style

- Python: Follow PEP 8, enforced by ruff
- TypeScript: Follow the ESLint configuration
- Commit messages: Use conventional commits

## Testing

- Run all tests: `just test`
- Backend tests: `cd backend && uv run pytest`
- Frontend tests: `cd frontend && npm test`

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Ensure all tests pass
4. Submit a pull request with a clear description
