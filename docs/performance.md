# VinylDigger Performance Tuning Guide

*Last updated: July 2025*

## Overview

This guide provides comprehensive performance optimization strategies for VinylDigger, covering database optimization, caching strategies, API performance, and frontend optimization.

## Table of Contents

- [Database Performance](#database-performance)
- [API Performance](#api-performance)
- [Caching Strategies](#caching-strategies)
- [Background Job Optimization](#background-job-optimization)
- [Frontend Performance](#frontend-performance)
- [Monitoring Performance](#monitoring-performance)
- [Load Testing](#load-testing)

## Database Performance

### Connection Pooling

Configure optimal connection pool settings in your database configuration:

```python
# backend/src/core/database.py
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,          # Number of persistent connections
    max_overflow=40,       # Maximum overflow connections
    pool_timeout=30,       # Timeout for getting connection
    pool_recycle=3600,     # Recycle connections after 1 hour
    pool_pre_ping=True,    # Verify connections before use
)
```

### Indexing Strategy

Create indexes on frequently queried columns:

```sql
-- User queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Search queries
CREATE INDEX idx_searches_user_id ON saved_searches(user_id);
CREATE INDEX idx_searches_next_run ON saved_searches(next_run_at);
CREATE INDEX idx_searches_active ON saved_searches(is_active);

-- Search results queries
CREATE INDEX idx_results_search_id ON search_results(search_id);
CREATE INDEX idx_results_created_at ON search_results(created_at);
CREATE INDEX idx_results_price ON search_results(price);

-- OAuth tokens lookup
CREATE INDEX idx_oauth_tokens_user_provider ON oauth_tokens(user_id, provider);
CREATE INDEX idx_app_config_provider ON app_config(provider);

-- Price history analysis
CREATE INDEX idx_price_history_item_date ON price_history(item_id, date);
```

### Query Optimization

1. **Use Eager Loading** to prevent N+1 queries:

```python
# Bad - N+1 queries
searches = await db.execute(select(SavedSearch))
for search in searches:
    results = await db.execute(
        select(SearchResult).where(SearchResult.search_id == search.id)
    )

# Good - Single query with join
searches = await db.execute(
    select(SavedSearch)
    .options(selectinload(SavedSearch.results))
)
```

2. **Use Bulk Operations**:

```python
# Bad - Multiple inserts
for item in items:
    db.add(SearchResult(**item))
    await db.commit()

# Good - Bulk insert
await db.execute(
    insert(SearchResult),
    items
)
await db.commit()
```

### Database Maintenance

```bash
# Regular maintenance tasks
# Add to crontab or scheduler

# Analyze tables for query planning
echo "ANALYZE;" | docker-compose exec -T postgres psql -U postgres vinyldigger

# Vacuum to reclaim space
echo "VACUUM ANALYZE;" | docker-compose exec -T postgres psql -U postgres vinyldigger

# Reindex for performance
echo "REINDEX DATABASE vinyldigger;" | docker-compose exec -T postgres psql -U postgres vinyldigger
```

## API Performance

### Async Optimization

Leverage FastAPI's async capabilities:

```python
# Parallel external API calls
async def search_all_platforms(query: str):
    # Run searches concurrently
    discogs_task = search_discogs(query)
    ebay_task = search_ebay(query)

    discogs_results, ebay_results = await asyncio.gather(
        discogs_task,
        ebay_task
    )

    return combine_results(discogs_results, ebay_results)
```

### Response Optimization

1. **Pagination** for large datasets:

```python
@router.get("/searches/{search_id}/results")
async def get_search_results(
    search_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    results = await db.execute(
        select(SearchResult)
        .where(SearchResult.search_id == search_id)
        .offset(skip)
        .limit(limit)
    )
    return results.scalars().all()
```

2. **Field Selection** to reduce payload:

```python
# Allow clients to specify fields
@router.get("/searches")
async def get_searches(
    fields: list[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if fields:
        # Select only requested fields
        stmt = select(*[getattr(SavedSearch, f) for f in fields])
    else:
        stmt = select(SavedSearch)
```

### Gunicorn Configuration

For production deployment:

```python
# gunicorn.conf.py
import multiprocessing

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Performance
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Preloading
preload_app = True
```

## Caching Strategies

### Redis Caching Implementation

```python
# backend/src/core/cache.py
from __future__ import annotations  # Required for Python 3.13+ compatibility

from typing import Optional, Any
import json
import redis.asyncio as redis
from functools import wraps

class Cache:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, expire: int = 3600):
        await self.redis.set(
            key,
            json.dumps(value),
            ex=expire
        )

    async def invalidate(self, pattern: str):
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)

# Cache decorator
def cache_result(expire: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check cache
            cached = await cache.get(cache_key)
            if cached:
                return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache.set(cache_key, result, expire)

            return result
        return wrapper
    return decorator
```

### Caching Strategy by Data Type

```python
# User data - cache for 5 minutes
@cache_result(expire=300)
async def get_user_profile(user_id: str):
    # Fetch user data
    pass

# Search results - cache for 1 hour
@cache_result(expire=3600)
async def get_search_results(search_id: int, page: int):
    # Fetch paginated results
    pass

# External API responses - cache for 24 hours
@cache_result(expire=86400)
async def fetch_discogs_item(item_id: str):
    # Fetch from Discogs API
    pass
```

## Background Job Optimization

### Celery Worker Configuration

```python
# backend/src/workers/celery_app.py
app = Celery("vinyldigger")

app.conf.update(
    # Performance settings
    task_compression = "gzip",
    task_serializer = "json",
    result_compression = "gzip",
    result_serializer = "json",

    # Worker settings
    worker_prefetch_multiplier = 4,
    worker_max_tasks_per_child = 1000,

    # Task execution
    task_acks_late = True,
    task_reject_on_worker_lost = True,

    # Batching
    task_routes = {
        'search.execute': {'queue': 'searches'},
        'sync.collection': {'queue': 'sync'},
    }
)
```

### Task Optimization

```python
# Batch processing
@celery.task
async def process_search_batch(search_ids: list[int]):
    # Process multiple searches in one task
    results = []
    for search_id in search_ids:
        result = await execute_search(search_id)
        results.append(result)
    return results

# Rate limiting for external APIs
@celery.task(rate_limit="10/m")  # 10 per minute
async def fetch_from_discogs(item_id: str):
    # Respects Discogs rate limits
    pass
```

## Frontend Performance

### Build Optimization

```javascript
// vite.config.ts
export default defineConfig({
  build: {
    // Enable minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },

    // Code splitting
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
          'utils': ['clsx', 'date-fns', 'zod'],
        },
      },
    },

    // Optimize chunk size
    chunkSizeWarningLimit: 1000,
  },
});
```

### React Performance

1. **Component Memoization**:

```typescript
// Memoize expensive components
export const SearchResultCard = React.memo(({ result }: Props) => {
  return (
    <Card>
      {/* Component content */}
    </Card>
  );
}, (prevProps, nextProps) => {
  // Custom comparison
  return prevProps.result.id === nextProps.result.id;
});
```

2. **Lazy Loading**:

```typescript
// Lazy load routes
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Settings = React.lazy(() => import('./pages/Settings'));

// Use with Suspense
<Suspense fallback={<Loading />}>
  <Routes>
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/settings" element={<Settings />} />
  </Routes>
</Suspense>
```

3. **Virtual Scrolling** for large lists:

```typescript
import { FixedSizeList } from 'react-window';

const SearchResults = ({ results }) => (
  <FixedSizeList
    height={600}
    itemCount={results.length}
    itemSize={120}
    width='100%'
  >
    {({ index, style }) => (
      <div style={style}>
        <SearchResultCard result={results[index]} />
      </div>
    )}
  </FixedSizeList>
);
```

### Network Optimization

1. **Request Deduplication** with React Query:

```typescript
// Queries with same key are automatically deduplicated
const { data: user } = useQuery({
  queryKey: ['user', userId],
  queryFn: () => api.getUser(userId),
  staleTime: 5 * 60 * 1000, // 5 minutes
});
```

2. **Prefetching**:

```typescript
// Prefetch next page
const queryClient = useQueryClient();

const prefetchNextPage = (page: number) => {
  queryClient.prefetchQuery({
    queryKey: ['results', page + 1],
    queryFn: () => api.getResults(page + 1),
  });
};
```

## Monitoring Performance

### Application Metrics

```python
# backend/src/core/metrics.py
from prometheus_fastapi_instrumentator import Instrumentator
import time
from functools import wraps

# Initialize Prometheus metrics
instrumentator = Instrumentator()

# Custom metrics
request_duration = instrumentator.registry.histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint", "status"]
)

# Performance monitoring decorator
def monitor_performance(endpoint: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status = "success"
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                request_duration.labels(
                    method=kwargs.get("request", {}).method,
                    endpoint=endpoint,
                    status=status
                ).observe(duration)
            return result
        return wrapper
    return decorator
```

### Database Query Monitoring

```python
# Log slow queries
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.5:  # Log queries taking more than 500ms
        logger.warning(
            f"Slow query detected ({total:.2f}s): {statement[:100]}..."
        )
```

## Load Testing

### Using Locust

Create a `locustfile.py`:

```python
from locust import HttpUser, task, between

class VinylDiggerUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login
        response = self.client.post("/api/v1/auth/login", data={
            "username": "test@example.com",
            "password": "testpassword"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def view_searches(self):
        self.client.get("/api/v1/searches", headers=self.headers)

    @task(2)
    def view_search_results(self):
        self.client.get("/api/v1/searches/1/results", headers=self.headers)

    @task(1)
    def create_search(self):
        self.client.post("/api/v1/searches",
            headers=self.headers,
            json={
                "name": "Test Search",
                "artist": "Pink Floyd",
                "min_condition": "VG"
            }
        )
```

Run load tests:

```bash
# Install Locust
pip install locust

# Run with 100 users
locust -f locustfile.py -H http://localhost:8000 -u 100 -r 10
```

## Performance Checklist

### Backend
- [ ] Database indexes created
- [ ] Connection pooling configured
- [ ] Query optimization implemented
- [ ] Caching layer active
- [ ] Async operations used
- [ ] Bulk operations for large datasets
- [ ] Rate limiting configured

### Frontend
- [ ] Code splitting enabled
- [ ] Lazy loading implemented
- [ ] Components memoized
- [ ] Virtual scrolling for large lists
- [ ] Image optimization
- [ ] Bundle size optimized

### Infrastructure
- [ ] CDN configured
- [ ] Gzip compression enabled
- [ ] HTTP/2 enabled
- [ ] SSL/TLS optimized
- [ ] Load balancing configured

### Monitoring
- [ ] APM tool configured
- [ ] Slow query logging
- [ ] Error tracking
- [ ] Performance metrics collected
- [ ] Alerts configured

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time (p95) | < 200ms | Prometheus/APM |
| Database Query Time (p95) | < 100ms | PostgreSQL logs |
| Frontend Load Time | < 3s | Lighthouse |
| Time to Interactive | < 5s | Lighthouse |
| Search Execution Time | < 30s | Celery metrics |
| Cache Hit Rate | > 80% | Redis metrics |

## Recent Performance Improvements

### Python 3.13 Compatibility
- **Redis Type Annotations**: Fixed runtime errors with `from __future__ import annotations`
- **Performance Impact**: Minimal - only affects import time, not runtime performance
- **Best Practice**: Always include future annotations import when using Redis with Python 3.13+

### Database Constraint Optimizations
- **Foreign Key Validation**: Improved with proper enum usage for platform fields
- **Index Usage**: Better query planning with consistent lowercase platform values
- **Bulk Operations**: Enhanced error handling for batch inserts

## Troubleshooting Performance Issues

### High API Latency
1. Check database query performance
2. Verify connection pool health
3. Review cache hit rates
4. Check for N+1 queries

### Slow Frontend
1. Analyze bundle size
2. Check for render blocking resources
3. Review component re-renders
4. Verify lazy loading implementation

### Database Bottlenecks
1. Run EXPLAIN ANALYZE on slow queries
2. Check for missing indexes
3. Review connection pool usage
4. Consider read replicas

### Memory Issues
1. Profile Python memory usage
2. Check for memory leaks in workers
3. Review Redis memory usage
4. Optimize data structures
