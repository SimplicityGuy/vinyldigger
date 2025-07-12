# VinylDigger 🎵

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178c6.svg)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-dc382d.svg)](https://redis.io/)
[![Node.js](https://img.shields.io/badge/Node.js-22-339933.svg)](https://nodejs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4.0-38B2AC.svg)](https://tailwindcss.com/)
[![uv](https://img.shields.io/badge/uv-0.5-purple.svg)](https://github.com/astral-sh/uv)

[![CI](https://github.com/SimplicityGuy/vinyldigger/workflows/CI/badge.svg)](https://github.com/SimplicityGuy/vinyldigger/actions)
[![Build](https://github.com/SimplicityGuy/vinyldigger/workflows/Build%20and%20Push%20Docker%20Images/badge.svg)](https://github.com/SimplicityGuy/vinyldigger/actions)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful web application that automates vinyl record discovery and comparison across Discogs and eBay, helping collectors find the best deals while considering their collection and want list.

## 🚀 Features

### 🔍 Smart Search Integration
- **Cross-Platform Search**: Search both eBay and Discogs simultaneously
- **Want List Matching**: Automatically identify items from your Discogs want list
- **Collection Awareness**: Skip items you already own
- **Seller Optimization**: Find sellers with multiple items to save on shipping
- **Flexible Sync Options**: Sync collection and want list together or separately

### 📊 Advanced Filtering
- **Per-Search Preferences**: Set condition and location preferences for each search
- **Condition Filtering**: Minimum acceptable conditions for records and sleeves
- **Location Preferences**: Filter by seller location (US, EU, UK, or worldwide)
- **Price History**: Track price changes over time
- **Automated Monitoring**: Schedule searches to run periodically

### 🔐 Security & Privacy
- **OAuth Authentication**: Secure OAuth integration for both Discogs (OAuth 1.0a) and eBay (OAuth 2.0)
- **Encrypted API Keys**: Legacy API credentials are encrypted at rest
- **JWT Authentication**: Secure token-based authentication
- **User Isolation**: Each user's data is completely isolated

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI with Python 3.13
- **Database**: PostgreSQL 16 with SQLAlchemy (async)
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery
- **Authentication**: JWT with passlib
- **API Documentation**: Auto-generated OpenAPI/Swagger

### Frontend
- **Framework**: React 19 with TypeScript 5.7
- **Build Tool**: Vite 6.0
- **Styling**: Tailwind CSS v4 with Radix UI
- **State Management**: TanStack Query (React Query)
- **Routing**: React Router v7
- **Forms**: React Hook Form with Zod validation

### DevOps & Tooling
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions with Dependabot
- **Code Quality**: Pre-commit hooks, Ruff, mypy, ESLint
- **Testing**: pytest, Vitest, Playwright
- **Package Management**: uv (Python), npm (Node.js)
- **Task Runner**: Just

## 📋 Prerequisites

- Docker and Docker Compose
- Git
- Just (recommended for convenience commands) - Install from https://github.com/casey/just
- For local development:
  - Python 3.13 with uv - Install from https://github.com/astral-sh/uv
  - Node.js 22+ with npm

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/SimplicityGuy/vinyldigger.git
   cd vinyldigger
   ```

2. **Set up environment**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your configuration
   # Note: API keys for Discogs/eBay are now optional - OAuth is preferred
   ```

3. **Start the application**
   ```bash
   just up
   # Or without just: docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs

## 🔧 Development Setup

### Initial Setup
```bash
# Install all dependencies and pre-commit hooks
just install
```

### Backend Development
```bash
# Start backend development server
just dev-backend

# Or manually:
cd backend
uv sync --dev
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
# Start frontend development server
just dev-frontend

# Or manually:
cd frontend
npm ci
npm run dev
```

### Code Quality
```bash
# Run all pre-commit checks
just lint

# Format code
just format

# Type checking
just typecheck

# Update pre-commit hooks
just update-pre-commit
```

### Run Tests
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

See the [Testing Guide](docs/testing.md) for detailed testing instructions.

## 📚 Documentation

### Documentation Hub
📖 **[View Complete Documentation Index](docs/README.md)** - Comprehensive guide to all documentation

### Quick Links
- [API Documentation](docs/api.md) - Complete REST API reference with examples
- [API Client Examples](docs/api-examples.md) - Example code in multiple languages
- [Architecture Overview](docs/architecture.md) - System design and technical details
- [Testing Guide](docs/testing.md) - Running and writing tests
- [Deployment Guide](docs/deployment.md) - Production deployment instructions
- [Performance Tuning](docs/performance.md) - Optimization strategies and best practices
- [Security Guide](docs/security.md) - Security best practices and implementation
- [Monitoring & Observability](docs/monitoring.md) - Logging, metrics, and alerting
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute to the project
- [E2E Testing Guide](frontend/tests/e2e/README.md) - End-to-end testing documentation

### Additional Documentation
- [OAuth Setup Guide](docs/oauth-setup.md) - Complete OAuth setup for Discogs and eBay
- [Troubleshooting Guide](docs/troubleshooting.md) - Common issues and solutions
- [Database Development Workflow](backend/docs/development_db_workflow.md) - Database management during development
- [Discogs OAuth Authentication](backend/docs/discogs_auth.md) - Technical implementation details
- [Docker OCI Labels](docs/docker-oci-labels.md) - Container labeling standards
- [Project Context](CLAUDE.md) - AI assistant configuration and project guidelines

### Interactive API Documentation
Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI Schema**: http://localhost:8000/api/openapi.json

### Key API Endpoints
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/searches` - List saved searches
- `POST /api/v1/searches` - Create new search
- `POST /api/v1/collections/sync` - Sync Discogs collection and want list
- `POST /api/v1/collections/sync/collection` - Sync collection only
- `POST /api/v1/collections/sync/wantlist` - Sync want list only

See the [complete API documentation](docs/api.md) for all endpoints and examples.

## 🐳 Docker Commands

```bash
# Build images
just build

# Start services
just up

# View logs
just logs

# Stop services
just down

# Clean up
just clean

# Run database migrations
just migrate

# Open shell in backend container
just shell-backend

# Open PostgreSQL shell
just shell-db
```

## 🔐 Configuration

### Platform Authorization
After registering and logging in, authorize VinylDigger to access your accounts:

1. **Discogs Authorization**
   - Go to Settings > Platform Authorizations
   - Click "Connect Discogs Account"
   - Authorize VinylDigger to access your Discogs data
   - See [Discogs OAuth Guide](backend/docs/discogs_auth.md) for details

2. **eBay Authorization** (Coming Soon)
   - OAuth integration for eBay is in development
   - Will follow similar authorization flow as Discogs

### Environment Variables
Key environment variables in `.env`:
```bash
# Application
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/vinyldigger

# Redis
REDIS_URL=redis://localhost:6379

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000
```

See `.env.example` for all available configuration options.

## 🏗️ Project Structure

```
vinyldigger/
├── backend/                # FastAPI backend
│   ├── src/               # Source code
│   │   ├── api/v1/        # API endpoints
│   │   ├── core/          # Core utilities
│   │   ├── models/        # Database models
│   │   ├── services/      # Business logic
│   │   └── workers/       # Background tasks
│   ├── tests/             # Backend tests
│   └── alembic/           # Database migrations
├── frontend/              # React frontend
│   ├── src/               # Source code
│   │   ├── components/    # UI components
│   │   ├── pages/         # Page components
│   │   ├── hooks/         # Custom hooks
│   │   ├── lib/           # Utilities
│   │   └── services/      # API client
│   └── tests/             # Frontend tests
├── docs/                  # Documentation
├── docker-compose.yml     # Docker configuration
├── justfile              # Task automation
└── .env.example          # Environment template
```

## 🚨 Troubleshooting

### Common Issues

#### Docker Issues
- **Containers not starting**: Run `just clean` to reset everything
- **Port conflicts**: Ensure ports 3000, 8000, 5432, 6379 are free
- **Volume permissions**: Check Docker has proper file permissions
- **Inter-container networking**: Use service names (e.g., `backend:8000`) not localhost

#### Development Issues
- **Import errors**: Check for circular imports, use TYPE_CHECKING
- **Type errors**: Run `just typecheck` to see all issues
- **Pre-commit failures**: Run `just lint` to see specific problems

#### Database Issues
- **Missing tables error**: Run `just migrate` to apply migrations
- **Development changes**: See [Database Development Workflow](backend/docs/development_db_workflow.md)
- **Connection errors**: Check DATABASE_URL in backend/.env matches docker-compose
- **Clean slate**: Use `just clean` to remove all containers and volumes

#### API Issues
- **401 Unauthorized**: Token may be expired, try logging in again
- **500 Internal Server Error**: Check backend logs with `just logs backend`
- **CORS errors**: Check FRONTEND_URL in backend .env


## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- UI components from [Radix UI](https://www.radix-ui.com/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)
- State management by [TanStack Query](https://tanstack.com/query)

## 📞 Support

- Create an issue for bug reports or feature requests
- Check the [API documentation](docs/api.md) or interactive docs at http://localhost:8000/api/docs
- Review [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- See [Architecture documentation](docs/architecture.md) for system design details
- Consult the [Testing guide](docs/testing.md) for test instructions
- Follow the [Deployment guide](docs/deployment.md) for production setup

---

Made with ❤️ for vinyl collectors everywhere
