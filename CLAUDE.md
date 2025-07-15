# VinylDigger Project Context

## Project Overview
VinylDigger is a web application that automates vinyl record discovery across Discogs and eBay. It helps record collectors find the best deals by monitoring both platforms, matching against their want list, and identifying sellers with multiple desired items to optimize shipping costs.

## Core Features

### User Experience
1. **Editable Saved Searches**: Complete CRUD functionality for saved searches
2. **Enhanced Price Comparison UI**: Expandable album groupings with clean organization
3. **Direct Links**: One-click access to eBay listings and Discogs release pages
4. **Dashboard Improvements**: 4-card stats grid, recent activity feed, and real-time sync status
5. **Profile Management**: Editable email addresses with proper validation
6. **Member Since Fix**: Proper account creation date display in settings
7. **OAuth Authentication**: Full OAuth support for both Discogs and eBay platforms

### Technical Improvements
- **Backend API Enhancements**: New PUT endpoint for search updates with partial update support
- **Frontend State Management**: Improved React Query usage with better invalidation patterns
- **Real-time Updates**: Intelligent sync completion detection without manual page refreshes
- **Enhanced Error Handling**: Better user feedback and error states throughout the application
- **Python 3.13 Compatibility**: Fixed Redis type annotation issues with `from __future__ import annotations`
- **Database Constraints**: Enhanced foreign key validation with proper enum usage
- **Docker Standards**: Implemented OCI labels compliance with hadolint validation
- **Test Coverage**: Comprehensive test suite with proper mocking patterns
- **Marketplace Search Implementation**: Complete rewrite of Discogs search to use marketplace API instead of catalog database

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
- **TypeScript 5.7**: Type safety for the frontend
- **PostgreSQL 16**: Robust relational database with JSON support
- **Redis 7**: Cache and message broker for Celery (with Python 3.13 compatibility fixes)
- **Docker**: Containerization with OCI standard labels compliance
- **Tailwind CSS v4**: Utility-first CSS framework
- **Vite 6**: Fast build tool and dev server
- **uv**: Fast Python package installer and resolver
- **Just**: Command runner for project tasks
- **Hadolint**: Docker best practices enforcement

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

### OAuth Authentication
1. **Discogs OAuth 1.0a**: Request token → User authorization → Access token
2. **eBay OAuth 2.0**: Authorization code → Exchange for access token
3. Both support manual code entry for environments without redirects
4. OAuth tokens stored encrypted in database

### API Key Security
- User API keys are encrypted using Fernet symmetric encryption (legacy)
- Keys are never logged or exposed in responses
- Separate encryption for each service (Discogs, eBay)
- OAuth is preferred over API keys for security

### Background Task Architecture
1. **Celery Workers**: Handle search execution and collection sync
2. **APScheduler**: Triggers periodic tasks
3. **Redis**: Message broker between services
4. **Task States**: Tracked in PostgreSQL

### Search & Analysis Workflow

#### Search Execution
1. **User creates saved search** with criteria and frequency preference
2. **Scheduler checks for due searches** every hour via APScheduler
3. **Worker executes marketplace search** across Discogs marketplace and eBay platforms
4. **Analysis runs immediately** after search completion
5. **Results stored** with collection/want list matching and analysis data
6. **Price history tracked** for trends over time

#### Marketplace Search Implementation (January 2025)

**Critical Architecture Change**: VinylDigger now searches actual marketplace listings instead of catalog databases.

**Discogs Integration**:
- **Endpoint**: `/marketplace/search` (was `/database/search`)
- **Data Source**: Live marketplace listings with real prices and sellers
- **Filters**: Condition (media/sleeve), seller location, price range
- **Results**: Actual items for sale with asking prices

**Key Benefits**:
- **Real Pricing**: Actual asking prices instead of "Price TBD"
- **Seller Information**: Complete seller details, ratings, and location
- **Marketplace Filters**: Filter by condition, location, and price range
- **Multi-item Detection**: Identify sellers with multiple wanted items
- **Accurate Analysis**: Price comparisons use real marketplace data

**Data Structure Changes**:
- **Listing IDs**: Use marketplace listing IDs for uniqueness
- **Release IDs**: Cross-reference collection/wantlist using release IDs
- **Seller Data**: Extract comprehensive seller information from listings
- **Condition Data**: Capture both media and sleeve condition ratings
- **Shipping Costs**: Include estimated shipping where available

#### Analysis Frequency & Execution Model

**Analysis is Event-Driven**: Analysis occurs every time a search executes, not on an independent schedule.

**Search Frequency** (User Configurable):
- **Default**: Every 24 hours per saved search
- **Configurable**: 6, 12, 24, 48+ hours via `check_interval_hours`
- **Manual**: Users can trigger immediate searches anytime

**What Gets Analyzed Each Time**:
- **Item Matching**: Cross-platform item identification using fuzzy matching
- **Seller Analysis**: Reputation scoring, inventory depth, location preferences
- **Deal Recommendations**: Multi-item opportunities, shipping cost optimization
- **Collection/Wantlist Matching**: Against user's Discogs collection data
- **Price Comparison**: Historical pricing and market trends

**Analysis Results**:
- **Immediately Available**: Via `/api/v1/analysis/search/{id}/...` endpoints
- **Cached Until Next Run**: Analysis data persists until search re-executes
- **Progressive Enhancement**: New searches add to historical analysis data

**Performance Characteristics**:
- **Concurrent Processing**: Multiple searches can run simultaneously via Celery workers
- **Scalable**: Worker pool can be scaled based on user demand
- **Efficient**: Results cached in database, no redundant analysis calls

## Development Guidelines

### Code Quality
- **Pre-commit Hooks**: Enforce code standards before commit
- **Type Checking**: mypy for Python, TypeScript for frontend
- **Linting**: Ruff for Python, ESLint v9 for TypeScript
- **Testing**: pytest for backend, Vitest for frontend
- **Formatting**: Ruff for Python, Prettier for TypeScript

### Development Workflow
```bash
# Install all dependencies
just install

# Run pre-commit checks (ALWAYS run before committing)
just lint

# Format code
just format

# Type check
just typecheck

# Run tests locally
just test-local

# Update dependencies
just update-pre-commit
```

### Platform Naming Conventions
- **In code**: Always use lowercase (e.g., `"discogs"`, `"ebay"`)
- **In UI**: Use proper capitalization (e.g., "Discogs", "eBay")
- **In database**: Store as lowercase for consistency
- **Common mistake**: Using `"DISCOGS"` or `"Discogs"` in backend code

### Database Development Workflow
During development, we use a simplified approach:
- **Single initial migration** contains all current models
- **Drop and recreate** database when models change
- **Alembic remains configured** for future production use

```bash
# Development: Drop and recreate database
just down
docker volume rm vinyldigger_postgres_data
just up

# Production (future): Create migrations
cd backend
uv run alembic revision --autogenerate -m "Description"
uv run alembic upgrade head
```

See `backend/docs/development-db-workflow.md` for detailed instructions.

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
- **Always run lint checks before tests**: `just lint` catches issues early
- **Platform name consistency**: Use lowercase in code (e.g., `platform="discogs"`)

### Frontend Tests
- Unit tests with Vitest
- Component testing with Testing Library
- E2E tests with Playwright
- Mock API responses for isolation
- **TypeScript type safety**: Ensure mocks match actual API response types
- **Mock setup patterns**: Create reusable mock factories for consistent testing

### Testing Best Practices
1. **Run lint before committing**: `just lint` catches formatting, type, and style issues
2. **Test locally first**: Use `just test-local` for faster feedback during development
3. **Mock external services**: Never make real API calls in tests
4. **Use meaningful test data**: Realistic data helps catch edge cases
5. **Test error cases**: Always test both success and failure scenarios
6. **Keep tests isolated**: Each test should be independent and repeatable

See `backend/docs/testing-guide.md` for comprehensive testing patterns and examples.

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

### Modifying Analysis Frequency
**To change default frequency**:
1. Update `check_interval_hours` default in `src/models/search.py`
2. Update API schema defaults in `src/api/v1/endpoints/searches.py`
3. Update config defaults in `src/api/v1/endpoints/config.py`

**Analysis execution flow**:
- `src/workers/scheduler.py` → Checks `SavedSearch.check_interval_hours`
- `src/workers/tasks.py` → `RunSearchTask` → Executes search + analysis
- `src/services/recommendation_engine.py` → Performs analysis logic
- Results stored in `search_analyses`, `deal_recommendations` tables

### Modifying Database Schema
**Development Workflow:**
1. Update SQLAlchemy model
2. Drop and recreate database: `just clean && just up`
3. Test with fresh database
4. Update related code

**Production Workflow (Future):**
1. Update SQLAlchemy model
2. Create migration: `cd backend && uv run alembic revision --autogenerate -m "Description"`
3. Review migration file
4. Test migration up/down
5. Deploy with migration

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
2. **Database Changes**: Drop and recreate with `just clean && just up`
3. **Docker Issues**: Clean volumes with `just clean`
4. **Type Errors**: Update type stubs, check mypy config

### Debugging Tips
- Use `docker-compose logs -f [service]` for logs
- Check Redis with `redis-cli` in container
- PostgreSQL shell: `just shell-db`
- API testing: Use /api/docs Swagger UI

## Future Enhancements
- Real-time notifications (WebSockets)
- Advanced search filters
- Price prediction ML model
- Mobile app
- Multi-language support
- Batch operations for saved searches
- Export functionality for search results

## Development Best Practices

### Essential Development Rules
1. **Always use uv** for Python package management - never use pip directly
2. **Use the justfile** for common commands, or add new commands if they're frequently used
3. **Run pre-commit checks** before committing: `just lint` or `pre-commit run --all-files`
4. **Keep pre-commit hooks frozen**: `just update-pre-commit` or `pre-commit autoupdate --freeze`
5. **GitHub Actions security**: Always pin non-GitHub/Docker actions to their SHA
6. **Docker networking**: Services must use container names (e.g., `backend:8000`) not localhost for inter-container communication
7. **Database migrations**: Always run migrations after model changes - backend startup runs them automatically if alembic/versions/ contains migration files
8. **Lint before committing**: Running `just lint` before commits saves time by catching issues early
9. **Consistent naming**: Use lowercase for platform names in code (`"discogs"`, not `"Discogs"` or `"DISCOGS"`)
10. **Test with mocks**: All external API calls should be mocked in tests
11. **UUID handling in tests**: Use UUID objects (`uuid4()`), not string UUIDs
12. **Async test patterns**: Use AsyncMock for async database operations
13. **Docker builds**: Use `./scripts/docker-build.sh` for OCI-compliant images
14. **Type annotations**: Include `from __future__ import annotations` when using Redis

### Quick Command Reference
```bash
# Development
just install          # Install all dependencies
just dev-backend      # Start backend dev server
just dev-frontend     # Start frontend dev server

# Code Quality
just lint             # Run all pre-commit checks
just format           # Format code
just typecheck        # Type check

# Testing
just test             # Run tests in Docker
just test-local       # Run tests locally
just test-backend     # Backend tests only
just test-frontend    # Frontend tests only

# Docker
just up               # Start all services
just down             # Stop all services
just logs             # View logs
just clean            # Clean up everything
```

### CI/CD Notes
- GitHub Actions are configured with:
  - Pre-commit checks run separately for better visibility
  - Dependabot for automatic dependency updates
  - SHA pinning for all third-party actions
  - Separate jobs for backend, frontend, and E2E tests
  - Docker image builds with OCI standard labels
  - Hadolint validation for Dockerfile best practices
  - Multi-browser E2E testing with Playwright

### Troubleshooting Tips
1. **Pre-commit failures**: Run `just lint` to see all issues
2. **Type errors**: Check both `mypy` (backend) and `tsc` (frontend) output
3. **Docker issues**: Use `just clean` to reset everything
4. **Dependency conflicts**: Delete lock files and regenerate with `just install`
5. **Missing database tables**: Ensure migrations exist in alembic/versions/ and run `just migrate`
6. **Frontend proxy errors**: Verify VITE_API_URL uses container names in Docker
7. **Test failures**: Check if mocks match actual API responses
8. **Database schema mismatches**: Verify SQLAlchemy models match migration files exactly
9. **Platform name errors**: Ensure using lowercase platform names in backend code
10. **Redis Type Errors**: Add `from __future__ import annotations` for Python 3.13 compatibility
11. **Foreign Key Errors**: Use proper SearchPlatform enums, not string values
12. **OAuth Token Length**: Database supports 5000-character tokens (auto-migrated)

## UI/UX Design Patterns

### Component Architecture
- **Atomic Design**: Build reusable components with consistent patterns
- **Accessibility**: Use semantic HTML and ARIA labels throughout
- **Responsive Design**: Mobile-first approach with Tailwind breakpoints
- **Loading States**: Skeleton screens and loading indicators for all async operations

### User Feedback Patterns
- **Toast Notifications**: Success, error, and info messages with useToast hook
- **Form Validation**: Real-time validation with react-hook-form
- **Optimistic Updates**: Immediate UI updates with rollback on failure
- **Progress Indicators**: Visual feedback for long-running operations

### Navigation & Layout
- **Consistent Header**: Navigation with user authentication state
- **Breadcrumbs**: Clear hierarchy and navigation paths
- **Quick Actions**: Context-appropriate buttons and shortcuts
- **Responsive Sidebar**: Collapsible navigation for mobile devices

### Data Presentation
- **Expandable Cards**: Information hierarchy with progressive disclosure
- **External Links**: Clear visual indicators for external navigation
- **Status Indicators**: Visual feedback for sync states and operation results
- **Real-time Updates**: Live data without manual page refreshes

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
