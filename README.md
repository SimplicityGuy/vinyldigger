# VinylDigger 🎵

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178c6.svg)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-dc382d.svg)](https://redis.io/)
[![Node.js](https://img.shields.io/badge/Node.js-22-339933.svg)](https://nodejs.org/)

[![CI](https://github.com/yourusername/vinyldigger/workflows/CI/badge.svg)](https://github.com/yourusername/vinyldigger/actions)
[![Build](https://github.com/yourusername/vinyldigger/workflows/Build%20and%20Push%20Docker%20Images/badge.svg)](https://github.com/yourusername/vinyldigger/actions)
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

### 📊 Advanced Filtering
- **Condition Filtering**: Set minimum acceptable conditions for records and sleeves
- **Location Preferences**: Filter by seller location (US or worldwide)
- **Price History**: Track price changes over time
- **Automated Monitoring**: Schedule searches to run periodically

### 🔐 Security & Privacy
- **Encrypted API Keys**: Your external API credentials are encrypted at rest
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
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS with Radix UI
- **State Management**: TanStack Query (React Query)
- **Routing**: React Router v7
- **Forms**: React Hook Form with Zod validation

### DevOps & Tooling
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **Code Quality**: Pre-commit hooks, Ruff, mypy
- **Testing**: pytest, Vitest, Playwright
- **Package Management**: uv (Python), npm (Node.js)

## 📋 Prerequisites

- Docker and Docker Compose
- Git
- Just (optional, for convenience commands) - Install from https://github.com/casey/just

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/vinyldigger.git
   cd vinyldigger
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
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

### Install Pre-commit Hooks
```bash
just install-pre-commit
# Or: pre-commit install
```

### Backend Development
```bash
cd backend
uv sync --dev
uv run uvicorn src.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Run Tests
```bash
# All tests
just test

# Backend tests
cd backend && uv run pytest

# Frontend tests
cd frontend && npm test

# E2E tests
cd frontend && npm run test:e2e
```

## 📚 API Documentation

Once the application is running, visit http://localhost:8000/api/docs for interactive API documentation.

### Key Endpoints
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/searches` - List saved searches
- `POST /api/v1/searches` - Create new search
- `POST /api/v1/collections/sync` - Sync Discogs collection

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
```

## 🔐 Configuration

### Required API Keys
After registering and logging in, add your API keys in the Settings page:

1. **Discogs API**
   - Get your keys at: https://www.discogs.com/settings/developers
   - Required: Consumer Key and Consumer Secret

2. **eBay API**
   - Register at: https://developer.ebay.com/
   - Required: Client ID and Client Secret

### Environment Variables
See `.env.example` for all available configuration options.

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
- Check the [API documentation](http://localhost:8000/api/docs)
- Review [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines

---

Made with ❤️ for vinyl collectors everywhere
