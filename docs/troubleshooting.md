# VinylDigger Troubleshooting Guide

*Last updated: July 2025*

## Overview

This guide covers common issues and their solutions when developing or deploying VinylDigger.

## Table of Contents

- [Development Issues](#development-issues)
- [Docker Issues](#docker-issues)
- [Database Issues](#database-issues)
- [API Issues](#api-issues)
- [Frontend Issues](#frontend-issues)
- [Authentication Issues](#authentication-issues)
- [Performance Issues](#performance-issues)
- [Testing Issues](#testing-issues)
- [Analysis & Search Issues](#analysis--search-issues)

## Development Issues

### Import Errors

**Problem**: Getting import errors like `ModuleNotFoundError` or circular import issues.

**Solutions**:
1. Check for circular imports using `TYPE_CHECKING`:
   ```python
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from .models import User  # Import only for type hints
   ```

2. Ensure you're in the correct virtual environment:
   ```bash
   cd backend
   uv sync --dev
   source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
   ```

### Type Errors

**Problem**: mypy or TypeScript showing type errors.

**Solutions**:
1. Run type checking to see all issues:
   ```bash
   just typecheck
   # Or separately:
   cd backend && uv run mypy .
   cd frontend && npm run typecheck
   ```

2. Update type stubs:
   ```bash
   cd backend && uv add --dev types-requests types-redis
   ```

### Redis Type Annotation Issues (Python 3.13)

**Problem**: Type errors with Redis in Python 3.13.

**Solution**: Add future annotations import:
```python
from __future__ import annotations
# At the top of files using Redis
```

This is already implemented in the codebase but may be needed for new files.

### Pre-commit Failures

**Problem**: Pre-commit hooks failing on commit.

**Solutions**:
1. Run all checks manually:
   ```bash
   just lint
   # Or:
   pre-commit run --all-files
   ```

2. Update pre-commit hooks:
   ```bash
   just update-pre-commit
   ```

3. Skip hooks temporarily (not recommended):
   ```bash
   git commit --no-verify
   ```

## Docker Issues

### Containers Not Starting

**Problem**: Docker containers fail to start or crash immediately.

**Solutions**:
1. Clean everything and restart:
   ```bash
   just clean
   just up
   ```

2. Check for port conflicts:
   ```bash
   # Check if ports are in use
   lsof -i :3000  # Frontend
   lsof -i :8000  # Backend
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   ```

3. Check Docker logs:
   ```bash
   docker-compose logs -f [service_name]
   # Or:
   just logs backend
   ```

### Inter-container Networking

**Problem**: Containers can't communicate with each other.

**Solution**: Use container service names, not localhost:
- Frontend → Backend: `http://backend:8000`
- Backend → PostgreSQL: `postgresql://user:pass@postgres:5432/db`
- Backend → Redis: `redis://redis:6379`

**Example** in docker-compose.override.yml:
```yaml
frontend:
  environment:
    - VITE_API_URL=http://backend:8000  # NOT http://localhost:8000
```

### Volume Permissions

**Problem**: Permission denied errors when accessing files.

**Solutions**:
1. Fix ownership:
   ```bash
   sudo chown -R $USER:$USER ./backend ./frontend
   ```

2. Rebuild without cache:
   ```bash
   docker-compose build --no-cache
   ```

## Database Issues

### Missing Tables Error

**Problem**: `sqlalchemy.exc.ProgrammingError: relation "users" does not exist`

**Solutions**:
1. Run migrations:
   ```bash
   just migrate
   # Or:
   docker-compose exec backend alembic upgrade head
   ```

2. If migrations folder is empty, create initial migration:
   ```bash
   docker-compose exec backend alembic revision --autogenerate -m "Initial migration"
   docker-compose exec backend alembic upgrade head
   ```

### Migration Conflicts

**Problem**: Alembic migration conflicts or "branch" errors.

**Solutions**:
1. Reset migrations in development:
   ```bash
   cd backend
   uv run alembic downgrade base
   uv run alembic upgrade head
   ```

2. Merge migration heads:
   ```bash
   cd backend
   uv run alembic merge -m "Merge migrations"
   ```

### Connection Errors

**Problem**: Can't connect to PostgreSQL.

**Solutions**:
1. Check DATABASE_URL in backend/.env:
   ```bash
   # For Docker:
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/vinyldigger

   # For local development:
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vinyldigger
   ```

2. Verify PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   docker-compose logs postgres
   ```

## API Issues

### 500 Internal Server Error

**Problem**: API returns 500 error without details.

**Solutions**:
1. Check backend logs:
   ```bash
   just logs backend
   # Or:
   docker-compose logs -f backend
   ```

2. Common causes:
   - Missing database tables (run migrations)
   - Missing environment variables
   - External API connection issues

### 401 Unauthorized

**Problem**: Getting 401 errors when calling authenticated endpoints.

**Solutions**:
1. Check if token is expired:
   - Access tokens expire after 30 minutes
   - Use refresh token to get new access token

2. Verify token format in request:
   ```javascript
   headers: {
     'Authorization': 'Bearer ' + accessToken  // Note the space after "Bearer"
   }
   ```

### CORS Errors

**Problem**: Browser shows CORS policy errors.

**Solutions**:
1. Check FRONTEND_URL in backend/.env:
   ```bash
   FRONTEND_URL=http://localhost:3000
   ```

2. For production, ensure all domains are listed:
   ```bash
   CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

## Frontend Issues

### Proxy Errors

**Problem**: Frontend can't reach backend API.

**Solutions**:
1. In development, check vite.config.ts:
   ```typescript
   proxy: {
     '/api': {
       target: process.env.VITE_API_URL || 'http://localhost:8000',
       changeOrigin: true,
     },
   },
   ```

2. Check docker-compose.override.yml:
   ```yaml
   frontend:
     environment:
       - VITE_API_URL=http://backend:8000
   ```

### Build Failures

**Problem**: Frontend fails to build.

**Solutions**:
1. Clean and reinstall:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

2. Check for TypeScript errors:
   ```bash
   npm run typecheck
   ```

## Authentication Issues

### Registration Fails

**Problem**: Can't create new accounts.

**Solutions**:
1. Check if email is already registered
2. Verify password meets requirements (min 8 characters)
3. Check backend logs for specific errors

### Login Fails

**Problem**: Valid credentials rejected.

**Solutions**:
1. Verify email format in login (uses email as username)
2. Check if account exists in database:
   ```sql
   SELECT * FROM users WHERE email = 'user@example.com';
   ```

### eBay OAuth Issues

**Problem**: eBay authentication failing with various errors.

**Common Issues & Solutions**:

#### "401 Unauthorized" from eBay API
- **Cause**: Environment mismatch (sandbox credentials with production URLs)
- **Solution**: VinylDigger now auto-detects environment from App ID:
  - Sandbox App IDs contain `SBX` → uses sandbox endpoints
  - Production App IDs contain `PRD` → uses production endpoints
- **Check**: Verify your App ID matches the intended environment

#### "unauthorized_client" Error
- **Cause**: Redirect URI mismatch between eBay Developer App and VinylDigger config
- **Solution**: Ensure exact match (including HTTPS and trailing slashes):
  ```
  eBay Developer App: https://your-domain.com/api/v1/oauth/redirect/ebay
  VinylDigger Config:  https://your-domain.com/api/v1/oauth/redirect/ebay
  ```

#### "Invalid redirect_uri" Error
- **Cause**: eBay requires HTTPS public URLs (no localhost/HTTP)
- **Solutions**:
  1. Use ngrok: `ngrok http 8000` → `https://abc123.ngrok-free.app`
  2. Deploy static HTML redirect page (see [eBay Setup Guide](backend/ebay-developer-setup.md))
  3. Use cloud tunneling service

#### OAuth Token Too Long Error
- **Cause**: eBay tokens exceed database field limits
- **Solution**: Database now supports 5000-character tokens (auto-migrated)
- **Manual Fix**: If migration failed, run:
  ```sql
  ALTER TABLE oauth_tokens
  ALTER COLUMN access_token TYPE VARCHAR(5000),
  ALTER COLUMN access_token_secret TYPE VARCHAR(5000),
  ALTER COLUMN refresh_token TYPE VARCHAR(5000);
  ```

#### Scheduler Timezone Errors
- **Cause**: Mixing timezone-naive and timezone-aware datetime objects
- **Solution**: Fixed in latest version (uses UTC consistently)
- **Symptom**: `can't subtract offset-naive and offset-aware datetimes`

### Discogs OAuth Issues

**Problem**: Discogs authentication not working.

**Solutions**:
1. Verify Discogs app callback URL matches VinylDigger redirect URI
2. Check if using correct consumer key/secret pair
3. Ensure callback URL uses HTTPS in production

## Performance Issues

### Slow API Responses

**Problem**: API requests take too long.

**Solutions**:
1. Add database indexes:
   ```python
   # In SQLAlchemy models
   __table_args__ = (
       Index('idx_user_email', 'email'),
   )
   ```

2. Enable query logging to find slow queries:
   ```python
   # In backend/.env
   LOG_LEVEL=DEBUG
   ```

3. Use Redis caching for frequently accessed data

### High Memory Usage

**Problem**: Containers using too much memory.

**Solutions**:
1. Limit container memory in docker-compose.yml:
   ```yaml
   backend:
     deploy:
       resources:
         limits:
           memory: 512M
   ```

2. Optimize worker concurrency:
   ```bash
   # In docker-compose.yml
   worker:
     command: celery -A src.workers.celery_app worker --concurrency=2
   ```

## Quick Fixes Reference

| Issue | Command |
|-------|---------|
| Reset everything | `just clean && just up` |
| View logs | `just logs [service]` |
| Run migrations | `just migrate` |
| Type check | `just typecheck` |
| Lint code | `just lint` |
| Format code | `just format` |
| Run tests | `just test` |

## Testing Issues

### Platform Name Consistency

**Problem**: Tests failing due to platform name mismatches.

**Solution**: Always use lowercase platform names in code:
```python
# Correct
platform = "discogs"
platform = "ebay"

# Incorrect
platform = "Discogs"  # Will cause foreign key errors
platform = "DISCOGS"  # Will cause validation errors
```

### UUID Handling in Tests

**Problem**: Test failures when using string UUIDs.

**Solution**: Use UUID objects, not strings:
```python
# Correct
from uuid import uuid4
user_id = uuid4()

# Incorrect
user_id = "550e8400-e29b-41d4-a716-446655440000"
```

### Mock Type Mismatches

**Problem**: Mock objects don't match actual API response types.

**Solution**: Ensure mocks match the exact structure:
```python
# For async database operations
from unittest.mock import AsyncMock

mock_db = AsyncMock()
mock_db.query.return_value.filter.return_value.first.return_value = user
```

## Analysis & Search Issues

### Analysis Not Running

**Problem**: Search completes but analysis doesn't run.

**Key Points**:
- Analysis is event-driven - it runs automatically after each search
- There's no separate analysis schedule
- Check worker logs for analysis task execution

**Solutions**:
1. Verify worker is processing tasks:
   ```bash
   docker-compose logs worker | grep "analyze_search_results"
   ```

2. Check for analysis data:
   ```sql
   SELECT * FROM search_result_analyses WHERE search_id = 'your-search-id';
   ```

### Marketplace Search Issues

**Problem**: Getting "Price TBD" or no seller information.

**Solution**: Ensure using marketplace endpoint:
- The system should use `/marketplace/search` not `/database/search`
- Check `src/services/discogs.py` for correct endpoint
- Marketplace search provides real prices and seller data

### Foreign Key Constraint Errors

**Problem**: Database errors when saving search results.

**Solution**: Use proper enums for platform:
```python
from src.models.search import SearchPlatform

# Correct
search.platform = SearchPlatform.DISCOGS

# Incorrect
search.platform = "discogs"  # String will cause FK error
```

### Scheduler Timezone Issues

**Problem**: Tasks not running at expected times.

**Solution**: Set consistent timezone in environment:
```bash
# In .env or docker-compose.yml
TZ=America/Los_Angeles
SCHEDULER_TIMEZONE=America/Los_Angeles
```

Both must match for accurate scheduling.

### Analysis Frequency Configuration

**Problem**: Want to change how often analysis runs.

**Clarification**: Analysis runs with each search execution, not independently.

To change search frequency:
1. Update `check_interval_hours` in saved search
2. Default is 24 hours, configurable from 6-48+ hours
3. Analysis will run each time the search executes

## Getting Help

If you're still experiencing issues:

1. Check the [GitHub Issues](https://github.com/SimplicityGuy/vinyldigger/issues)
2. Review the [API Documentation](api.md)
3. Consult the [Architecture Guide](architecture.md)
4. Review [CLAUDE.md](../CLAUDE.md) for development best practices
5. Create a new issue with:
   - Description of the problem
   - Steps to reproduce
   - Error messages/logs
   - Environment details (OS, Docker version, etc.)
