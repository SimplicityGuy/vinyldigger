# VinylDigger Architecture Documentation

## System Overview

VinylDigger is a modern web application designed to help vinyl record collectors find the best deals across multiple marketplaces. The system employs a microservices architecture with clear separation between frontend, backend API, background workers, and scheduled tasks.

### Key Architecture Features

- **Enhanced UI/UX Layer**: Improved React components with better state management and real-time updates
- **Extended API Surface**: Additional endpoints for complete CRUD operations on user resources
- **Intelligent Client-Side Caching**: Optimized React Query usage with smart invalidation strategies
- **Real-time Feedback Systems**: Enhanced user experience with live status updates and completion detection
- **Improved Error Handling**: Better error boundaries and user feedback mechanisms throughout the application

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[React SPA]
        MOBILE[Mobile Web]
    end

    subgraph "API Layer"
        API[FastAPI Server]
        AUTH[JWT Auth]
    end

    subgraph "Service Layer"
        WORKER[Celery Workers]
        SCHEDULER[APScheduler]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL)]
        REDIS[(Redis)]
    end

    subgraph "External Services"
        DISCOGS[Discogs API]
        EBAY[eBay API]
    end

    WEB --> API
    MOBILE --> API
    API --> AUTH
    API --> PG
    API --> REDIS
    API --> WORKER
    SCHEDULER --> WORKER
    WORKER --> PG
    WORKER --> REDIS
    WORKER --> DISCOGS
    WORKER --> EBAY
```

## Technology Stack

### Backend
- **Language**: Python 3.13
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery 5.3
- **Scheduler**: APScheduler 3.10
- **Authentication**: JWT (python-jose)
- **Security**: passlib, cryptography (Fernet)

### Frontend
- **Language**: TypeScript 5.7
- **Framework**: React 19
- **Build Tool**: Vite 6
- **Styling**: Tailwind CSS v4
- **UI Components**: Radix UI
- **State Management**: TanStack Query
- **Routing**: React Router v7
- **Forms**: react-hook-form + Zod

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Process Management**: Gunicorn (production)
- **Reverse Proxy**: Nginx (production)
- **CI/CD**: GitHub Actions
- **Monitoring**: Structured logging (future: OpenTelemetry)

## Core Components

### 1. API Server (FastAPI)

The API server handles all HTTP requests and provides RESTful endpoints.

**Key Features**:
- Async request handling for high performance
- Automatic OpenAPI documentation
- Request validation with Pydantic
- Dependency injection for clean code
- CORS middleware for cross-origin requests

**Directory Structure**:
```
backend/src/
├── api/v1/
│   ├── endpoints/     # API route handlers
│   └── api.py         # Main API router
├── core/
│   ├── config.py      # Configuration management
│   ├── database.py    # Database connection
│   ├── logging.py     # Logging configuration
│   └── security.py    # Security utilities
├── models/            # SQLAlchemy models
├── services/          # Business logic layer
└── workers/           # Background task definitions
```

### 2. Background Workers (Celery)

Celery workers handle long-running tasks asynchronously.

**Task Types**:
- **Search Execution**: Queries external APIs and processes results
- **Collection Sync**: Synchronizes user's Discogs collection
- **Want List Sync**: Synchronizes user's Discogs want list
- **Data Processing**: Matches results against collections
- **Search Analysis**: Performs intelligent analysis of search results
- **Item Matching**: Cross-platform item matching and deduplication
- **Seller Analysis**: Evaluates sellers for multi-item opportunities
- **Recommendation Generation**: Creates smart deal recommendations

**Configuration**:
```python
# Celery configuration
broker_url = "redis://redis:6379/0"
result_backend = "redis://redis:6379/0"
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True
```

### 3. Task Scheduler (APScheduler)

APScheduler runs periodic tasks based on user preferences.

**Scheduled Tasks**:
- Check for due searches every hour
- Queue search execution tasks
- Clean up old search results (future)
- Generate reports (future)

### 4. Frontend Application (React)

Single-page application providing the user interface.

**Architecture Patterns**:
- Component-based architecture with atomic design principles
- Custom hooks for business logic and state management
- Context for authentication state
- React Query for server state management with intelligent caching
- Lazy loading for code splitting and performance
- Progressive disclosure UI patterns with expandable components
- Real-time updates without manual refresh requirements

**Recent UI/UX Enhancements**:
- **Editable Search Management**: Full CRUD operations with form validation
- **Enhanced Dashboard**: 4-card statistics grid with real-time sync detection
- **Improved Price Comparison**: Collapsible interface with expandable detailed views
- **Direct Navigation**: One-click links to external listings and release pages
- **Profile Management**: Inline editing with proper validation and error handling
- **Smart Notifications**: Toast-based feedback with success/error states

**Directory Structure**:
```
frontend/src/
├── components/        # Reusable UI components (cards, forms, modals)
├── pages/            # Route-based page components (enhanced UX)
├── hooks/            # Custom React hooks (useAuth, useToast)
├── lib/              # Utilities and API client (enhanced error handling)
├── services/         # API client services (optimized for React Query)
└── types/            # TypeScript type definitions (updated schemas)
```

## Data Architecture

### Database Schema

PostgreSQL database with the following main tables:

1. **users**: User accounts and authentication
2. **app_config**: OAuth application credentials (admin-configured)
3. **oauth_tokens**: User OAuth access tokens
4. **saved_searches**: User's search configurations
5. **search_results**: Cached search results
6. **collections**: User's vinyl collections
7. **collection_items**: Individual items in collections
8. **want_lists**: User's want lists
9. **want_list_items**: Individual items in want lists
10. **sellers**: Seller information across platforms
11. **item_matches**: Cross-platform item matching
12. **search_result_analyses**: Analysis data for completed searches
13. **seller_analyses**: Seller scoring and recommendation data
14. **deal_recommendations**: AI-generated deal recommendations

### Data Flow

1. **Search Flow**:

```mermaid
graph LR
    A[User creates search] --> B[API stores in DB]
    B --> C[Scheduler checks periodically]
    C --> D[Worker executes search]
    D --> E[Results stored in DB]
    E --> F[User views results]
```

2. **Collection Sync Flow**:

```mermaid
graph LR
    A[User triggers sync] --> B[API queues task]
    B --> C[Worker fetches from Discogs]
    C --> D[Data processed and stored]
    D --> E[Search results updated with matches]
```

3. **Enhanced Search Analysis Flow**:

```mermaid
graph TD
    A[Search Results Available] --> B[Item Matching Service]
    B --> C[Cross-Platform Deduplication]
    C --> D[Seller Analysis Service]
    D --> E[Multi-Item Opportunity Detection]
    E --> F[Recommendation Engine]
    F --> G[Deal Scoring & Ranking]
    G --> H[Analysis Results Stored]
    H --> I[API Endpoints Available]
```

## Analysis Engine Architecture

The Analysis Engine is a sophisticated system that processes search results to provide intelligent recommendations and insights.

### Core Components

1. **Item Matching Service**
   - **Purpose**: Identifies identical items across platforms
   - **Algorithm**: Fuzzy text matching with confidence scoring
   - **Features**:
     - Canonical title/artist normalization
     - Year and format matching
     - Confidence-based deduplication
     - Manual override support

2. **Seller Analysis Service**
   - **Purpose**: Evaluates sellers for optimization opportunities
   - **Metrics**:
     - Reputation scoring (0-100)
     - Location preference matching
     - Price competitiveness analysis
     - Inventory depth evaluation
     - Shipping cost estimation

3. **Recommendation Engine**
   - **Purpose**: Generates actionable deal recommendations
   - **Types**:
     - Multi-item deals (shipping optimization)
     - Best price recommendations
     - High-value discoveries
     - Collection completion suggestions

4. **Deal Scoring System**
   - **Scoring Levels**: Excellent (90+), Very Good (80+), Good (70+), Fair (60+), Poor (<60)
   - **Factors**:
     - Price competitiveness
     - Seller reputation
     - Shipping savings potential
     - Want list relevance

### Analysis Workflow

```mermaid
graph TD
    A[Search Completed] --> B{Results Available?}
    B -->|Yes| C[Extract Item Data]
    B -->|No| Z[End]
    C --> D[Find/Create Sellers]
    D --> E[Match Items Across Platforms]
    E --> F[Calculate Seller Metrics]
    F --> G[Find Multi-Item Opportunities]
    G --> H[Generate Recommendations]
    H --> I[Score All Deals]
    I --> J[Store Analysis Results]
    J --> K[Notify Analysis Complete]
```

### Analysis Data Models

1. **SearchResultAnalysis**
   - Aggregate statistics for the entire search
   - Completion status and timestamps
   - Price distribution metrics
   - Platform coverage analysis

2. **SellerAnalysis**
   - Individual seller performance metrics
   - Recommendation ranking
   - Scoring breakdowns by category
   - Multi-item potential assessment

3. **DealRecommendation**
   - Specific actionable recommendations
   - Deal type classification
   - Potential savings calculations
   - Item grouping for multi-item deals

### Performance Optimizations

1. **Async Processing**: All analysis runs in background workers
2. **Intelligent Caching**: Results cached until search data changes
3. **Incremental Updates**: Only reanalyze when new results arrive
4. **Batch Operations**: Group database operations for efficiency
5. **Selective Analysis**: Skip analysis for searches with minimal results

### Caching Strategy

Redis is used for:
- Celery task queue and results
- Session storage (future)
- API response caching (future)
- Rate limiting (future)

## Security Architecture

### Authentication & Authorization

1. **JWT Token Flow**:
   - User logs in with email/password
   - Server validates credentials
   - Server issues access token (30 min) and refresh token (7 days)
   - Client includes access token in Authorization header
   - Server validates token on each request

2. **Password Security**:
   - Passwords hashed using bcrypt
   - Configurable hash rounds
   - No password requirements (user's choice)

### OAuth Implementation

VinylDigger uses OAuth 1.0a for Discogs authentication:

```mermaid
graph TD
    subgraph "OAuth Flow"
        A1[User initiates authorization] --> B1[Request temporary token]
        B1 --> C1[Redirect to Discogs]
        C1 --> D1[User authorizes]
        D1 --> E1[Callback with verifier]
        E1 --> F1[Exchange for access token]
        F1 --> G1[Store encrypted token]
    end
```

**Key Components**:
- Application credentials stored in app_config (admin-managed)
- User tokens stored encrypted in oauth_tokens
- Fernet encryption for sensitive data
- Session management for OAuth flow state

### Security Headers

Production deployment includes:
- HTTPS enforcement
- CORS configuration
- Security headers (CSP, HSTS, etc.)
- Rate limiting
- Request size limits

## Performance Considerations

### Backend Optimization

1. **Async Operations**: All I/O operations are async
2. **Connection Pooling**: Database and Redis connection pools
3. **Query Optimization**: Indexed foreign keys and search fields
4. **Pagination**: Large result sets are paginated
5. **Background Processing**: Heavy operations run in Celery

### Frontend Optimization

1. **Code Splitting**: Routes are lazy loaded
2. **React Query**: Intelligent caching and refetching
3. **Optimistic Updates**: UI updates before server confirmation
4. **Bundle Optimization**: Tree shaking and minification
5. **Image Optimization**: Lazy loading and responsive images

## Scalability Architecture

### Horizontal Scaling

1. **API Servers**: Multiple instances behind load balancer
2. **Workers**: Scale based on queue depth
3. **Database**: Read replicas for heavy queries
4. **Redis**: Clustering for high availability

### Vertical Scaling

1. **Database**: Optimized queries and indexes
2. **Workers**: Concurrent task execution
3. **Caching**: Multi-layer caching strategy

## Development Workflow

### Local Development

```bash
# Start all services
just up

# Backend development
just dev-backend    # Hot reload enabled

# Frontend development
just dev-frontend   # HMR enabled

# Run tests
just test
```

### Git Workflow

1. **Branching Strategy**: Feature branches from main
2. **Commit Convention**: Conventional commits
3. **Code Review**: PR required for main branch
4. **CI/CD**: Automated tests on every push

## Deployment Architecture

### Container Strategy

Each service runs in its own container:
- `backend`: FastAPI application
- `worker`: Celery worker processes
- `scheduler`: APScheduler instance
- `frontend`: Nginx serving static files
- `postgres`: PostgreSQL database
- `redis`: Redis cache/queue

### Environment Configuration

Environment-specific settings:
- Development: `backend/.env` file with docker-compose.override.yml
- Production: Environment variables injected at runtime
- Secrets: Encrypted in deployment platform
- Database: Migrations run automatically on backend startup

## Monitoring and Observability

### Logging

Structured JSON logging with:
- Request IDs for tracing
- User context
- Performance metrics
- Error details with stack traces

### Health Checks

- `/health`: API server health
- Docker health checks for all services
- Database connection monitoring
- External API availability checks

### Metrics (Future)

Planned metrics collection:
- Request latency
- Task execution time
- Queue depth
- Cache hit rates
- External API response times

## Error Handling

### API Error Responses

Consistent error format:
```json
{
  "detail": "Human-readable error message"
}
```

### Background Task Errors

- Automatic retry with exponential backoff
- Dead letter queue for failed tasks
- Error notifications (future)

## External Integrations

### Discogs API

- Rate limiting: 60 requests/minute
- Authentication: OAuth 1.0a
- Used for: Collection sync, want list sync, search

### eBay API

- Rate limiting: 5000 requests/day
- Authentication: OAuth 2.0
- Used for: Product search, seller information

## Future Architecture Enhancements

1. **GraphQL API**: For more flexible data fetching
2. **WebSocket Support**: Real-time notifications
3. **Microservices**: Separate search service
4. **Event Sourcing**: Audit trail for all changes
5. **API Gateway**: Centralized routing and auth
6. **Service Mesh**: Inter-service communication
7. **Multi-tenancy**: Organization support
8. **Mobile Apps**: Native iOS/Android apps
