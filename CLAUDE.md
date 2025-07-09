# VinylDigger Project Context

## Project Overview
VinylDigger is a web application that automates vinyl record discovery across Discogs and eBay. It helps record collectors find the best deals by monitoring both platforms, matching against their want list, and identifying sellers with multiple desired items to optimize shipping costs.

## Key Technical Decisions

### Architecture
- **Monorepo Structure**: Backend and frontend in the same repository for easier development and deployment
- **Microservices Pattern**: Separate services for API, workers, and scheduler
- **Event-Driven**: Celery for background tasks, Redis for message broker
- **API-First Design**: FastAPI with automatic OpenAPI documentation

### Technology Choices
- **Python 3.13**: Latest version for performance improvements
- **FastAPI**: Modern, fast, async Python web framework
- **React 19**: Latest React with concurrent features
- **TypeScript**: Type safety for the frontend
- **PostgreSQL**: Robust relational database with JSON support
- **Redis**: Cache and message broker for Celery
- **Docker**: Containerization for consistent environments

### Code Organization

#### Backend Structure
```
backend/
├── src/
│   ├── api/v1/       # API endpoints
│   ├── core/         # Core utilities (config, security, database)
│   ├── models/       # SQLAlchemy models
│   ├── services/     # Business logic
│   └── workers/      # Background tasks
├── tests/            # Test suite
└── alembic/          # Database migrations
```

#### Frontend Structure
```
frontend/
├── src/
│   ├── components/   # Reusable UI components
│   ├── pages/        # Route components
│   ├── hooks/        # Custom React hooks
│   ├── lib/          # Utilities and API client
│   └── services/     # API integration
└── tests/            # Test suites
```

## Important Patterns

### Authentication Flow
1. User registers/logs in → JWT tokens issued
2. Access token for API requests (short-lived)
3. Refresh token for obtaining new access tokens
4. Tokens stored in localStorage (frontend)

### API Key Security
- User API keys are encrypted using Fernet symmetric encryption
- Keys are never logged or exposed in responses
- Separate encryption for each service (Discogs, eBay)

### Background Task Architecture
1. **Celery Workers**: Handle search execution and collection sync
2. **APScheduler**: Triggers periodic tasks
3. **Redis**: Message broker between services
4. **Task States**: Tracked in PostgreSQL

### Search Workflow
1. User creates saved search with criteria
2. Scheduler checks for due searches hourly
3. Worker executes search across platforms
4. Results stored with collection/want list matching
5. Price history tracked for trends

## Development Guidelines

### Code Quality
- **Pre-commit Hooks**: Enforce code standards before commit
- **Type Checking**: mypy for Python, TypeScript for frontend
- **Linting**: ruff for Python, ESLint for TypeScript
- **Testing**: pytest for backend, Vitest for frontend

### Database Migrations
```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### API Development
- All endpoints require authentication except health/auth routes
- Use Pydantic models for request/response validation
- Follow RESTful conventions
- Document with OpenAPI annotations

### Frontend State Management
- React Query for server state (API data)
- Local state with useState for UI state
- Form state with react-hook-form
- No global state management needed (yet)

## Testing Strategy

### Backend Tests
- Unit tests for services and utilities
- Integration tests for API endpoints
- Mock external APIs (Discogs, eBay)
- Use pytest fixtures for database sessions

### Frontend Tests
- Unit tests with Vitest
- Component testing with Testing Library
- E2E tests with Playwright
- Mock API responses for isolation

## Deployment Considerations

### Environment Variables
- `SECRET_KEY`: Must be unique per environment
- `DATABASE_URL`: PostgreSQL connection string
- API keys: Added via UI, not environment variables

### Docker Optimization
- Multi-stage builds for smaller images
- Layer caching for dependencies
- Health checks for all services
- Graceful shutdown handling

### Scaling Strategy
- Horizontal scaling for API (multiple instances)
- Worker scaling based on queue depth
- PostgreSQL read replicas for heavy loads
- Redis clustering if needed

## Common Tasks

### Adding a New API Endpoint
1. Create Pydantic schemas in endpoint file
2. Add endpoint function with proper dependencies
3. Include in router
4. Add tests
5. Update frontend API client

### Adding a New Background Task
1. Create task in `workers/tasks.py`
2. Add to Celery imports
3. Create service method to queue task
4. Add monitoring/logging

### Modifying Database Schema
1. Update SQLAlchemy model
2. Create migration: `alembic revision --autogenerate`
3. Review migration file
4. Test migration up/down
5. Update related code

## Security Best Practices
- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all user input
- Escape output in templates
- Use HTTPS in production
- Rate limit API endpoints
- Log security events

## Performance Optimization
- Database indexes on foreign keys and search fields
- Pagination for large result sets
- Caching with Redis for frequently accessed data
- Async operations where possible
- Connection pooling for database

## Troubleshooting

### Common Issues
1. **Import Errors**: Check for circular imports, use TYPE_CHECKING
2. **Migration Conflicts**: Reset migrations in development
3. **Docker Issues**: Clean volumes with `make clean`
4. **Type Errors**: Update type stubs, check mypy config

### Debugging Tips
- Use `docker-compose logs -f [service]` for logs
- Check Redis with `redis-cli` in container
- PostgreSQL shell: `make shell-db`
- API testing: Use /api/docs Swagger UI

## Future Enhancements
- OAuth2 integration for Discogs
- Real-time notifications (WebSockets)
- Advanced search filters
- Price prediction ML model
- Mobile app
- Multi-language support
