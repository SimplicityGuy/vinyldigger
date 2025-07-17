# VinylDigger Monitoring and Observability Guide

*Last updated: July 2025*

## Overview

This guide covers monitoring, logging, metrics collection, and observability practices for VinylDigger. It includes both application-level monitoring and infrastructure monitoring strategies.

## Table of Contents

- [Logging Strategy](#logging-strategy)
- [Metrics Collection](#metrics-collection)
- [Distributed Tracing](#distributed-tracing)
- [Health Checks](#health-checks)
- [Alerting](#alerting)
- [Dashboards](#dashboards)
- [Performance Monitoring](#performance-monitoring)
- [Security Monitoring](#security-monitoring)

## Logging Strategy

### Structured Logging Setup

```python
# backend/src/core/logging.py
import structlog
import logging
import sys
from pythonjsonlogger import jsonlogger

def configure_logging(log_level: str = "INFO"):
    """Configure structured JSON logging"""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.dict_tracebacks,
            structlog.processors.CallsiteParameter(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

# Usage
logger = structlog.get_logger(__name__)

# Log with context
logger.info("user_action",
    action="search_created",
    user_id=user_id,
    search_name=search.name,
    search_params=search.search_params
)
```

### Log Aggregation with ELK Stack

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  logstash:
    image: logstash:8.11.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline:ro
    environment:
      - "LS_JAVA_OPTS=-Xmx256m -Xms256m"
    depends_on:
      - elasticsearch

  kibana:
    image: kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  filebeat:
    image: elastic/filebeat:8.11.0
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    user: root
    depends_on:
      - logstash

volumes:
  es_data:
```

### Logstash Configuration

```ruby
# logstash/pipeline/logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  # Parse JSON logs
  json {
    source => "message"
    target => "parsed"
  }

  # Extract fields
  mutate {
    add_field => {
      "service" => "%{[parsed][service]}"
      "level" => "%{[parsed][level]}"
      "timestamp" => "%{[parsed][timestamp]}"
    }
  }

  # Parse timestamps
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }

  # Add GeoIP for IP addresses
  if [client_ip] {
    geoip {
      source => "client_ip"
      target => "geoip"
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "vinyldigger-%{+YYYY.MM.dd}"
  }
}
```

### Application Logging Best Practices

```python
# Log important events with context
class SearchService:
    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    async def execute_search(self, search_id: int) -> SearchResult:
        log = self.logger.bind(search_id=search_id)

        try:
            log.info("search_execution_started")
            start_time = time.time()

            # Execute search logic
            results = await self._perform_search(search_id)

            duration = time.time() - start_time
            log.info("search_execution_completed",
                    duration=duration,
                    result_count=len(results))

            return results

        except Exception as e:
            log.error("search_execution_failed",
                     error=str(e),
                     exc_info=True)
            raise
```

## Metrics Collection

### Prometheus Integration

```python
# backend/src/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_fastapi_instrumentator import Instrumentator
import time
from functools import wraps

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

active_searches = Gauge(
    'active_searches_total',
    'Number of active searches'
)

search_execution_duration = Histogram(
    'search_execution_duration_seconds',
    'Search execution duration',
    ['search_type', 'platform']
)

external_api_calls = Counter(
    'external_api_calls_total',
    'External API calls',
    ['service', 'endpoint', 'status']
)

app_info = Info('app_info', 'Application information')
app_info.info({
    'version': '1.0.0',
    'environment': 'production'
})

# Initialize Prometheus instrumentation
def setup_metrics(app):
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app)

# Metrics decorator
def track_metrics(endpoint: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            method = kwargs.get('request', {}).method or 'UNKNOWN'

            try:
                result = await func(*args, **kwargs)
                status = 'success'
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status
                ).inc()

                return result

            except Exception as e:
                status = 'error'
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status
                ).inc()
                raise

            finally:
                duration = time.time() - start_time
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)

        return wrapper
    return decorator
```

### Custom Business Metrics

```python
# Track business-specific metrics
class MetricsService:
    @staticmethod
    async def record_search_execution(search_type: str, platform: str, duration: float):
        search_execution_duration.labels(
            search_type=search_type,
            platform=platform
        ).observe(duration)

    @staticmethod
    async def record_api_call(service: str, endpoint: str, status: str):
        external_api_calls.labels(
            service=service,
            endpoint=endpoint,
            status=status
        ).inc()

    @staticmethod
    async def update_active_searches(count: int):
        active_searches.set(count)

# Usage in services
async def execute_discogs_search(query: str):
    start_time = time.time()
    try:
        result = await discogs_api.search(query)
        await MetricsService.record_api_call(
            service="discogs",
            endpoint="search",
            status="success"
        )
        return result
    except Exception as e:
        await MetricsService.record_api_call(
            service="discogs",
            endpoint="search",
            status="error"
        )
        raise
    finally:
        duration = time.time() - start_time
        await MetricsService.record_search_execution(
            search_type="vinyl",
            platform="discogs",
            duration=duration
        )
```

### Prometheus Configuration

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - "alerts/*.yml"

scrape_configs:
  - job_name: 'vinyldigger-api'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

## Distributed Tracing

### OpenTelemetry Setup

```python
# backend/src/core/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

def setup_tracing(app, service_name: str = "vinyldigger-api"):
    # Set up the tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # Configure OTLP exporter (e.g., to Jaeger)
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://jaeger:4317",
        insecure=True
    )

    # Add span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    # Instrument libraries
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    RequestsInstrumentor().instrument()

    return tracer

# Custom tracing decorator
def trace_operation(name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(name) as span:
                # Add custom attributes
                span.set_attribute("function.name", func.__name__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator
```

### Jaeger Configuration

```yaml
# docker-compose.tracing.yml
version: '3.8'

services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
```

## Health Checks

### Comprehensive Health Check Endpoint

```python
# backend/src/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import httpx
from datetime import datetime
from typing import Dict, Any

router = APIRouter()

class HealthChecker:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client

    async def check_database(self) -> Dict[str, Any]:
        try:
            result = await self.db.execute(text("SELECT 1"))
            return {"status": "healthy", "latency_ms": 0}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def check_redis(self) -> Dict[str, Any]:
        try:
            start = datetime.utcnow()
            await self.redis.ping()
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            return {"status": "healthy", "latency_ms": latency}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def check_external_apis(self) -> Dict[str, Any]:
        results = {}

        # Check Discogs API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.discogs.com/",
                    timeout=5.0
                )
                results["discogs"] = {
                    "status": "healthy" if response.status_code == 200 else "degraded",
                    "status_code": response.status_code
                }
        except Exception as e:
            results["discogs"] = {"status": "unhealthy", "error": str(e)}

        # Check eBay API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.ebay.com/",
                    timeout=5.0
                )
                results["ebay"] = {
                    "status": "healthy" if response.status_code < 500 else "degraded",
                    "status_code": response.status_code
                }
        except Exception as e:
            results["ebay"] = {"status": "unhealthy", "error": str(e)}

        return results

@router.get("/health/live")
async def liveness():
    """Basic liveness check"""
    return {"status": "alive"}

@router.get("/health/ready")
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Comprehensive readiness check"""
    checker = HealthChecker(db, redis_client)

    checks = {
        "database": await checker.check_database(),
        "redis": await checker.check_redis(),
        "external_apis": await checker.check_external_apis()
    }

    # Determine overall status
    overall_status = "healthy"
    for service, result in checks.items():
        if isinstance(result, dict) and result.get("status") == "unhealthy":
            overall_status = "unhealthy"
            break
        elif isinstance(result, dict) and result.get("status") == "degraded":
            overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }
```

### Kubernetes Health Probes

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vinyldigger-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: vinyldigger/api:latest
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        startupProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 0
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 30
```

## Alerting

### Alert Rules

```yaml
# prometheus/alerts/application.yml
groups:
  - name: application
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status="error"}[5m])) /
          sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 5% for the last 5 minutes"

      - alert: SlowAPIResponse
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow API responses"
          description: "95th percentile response time is above 1 second"

      - alert: DatabaseConnectionFailure
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "Cannot connect to PostgreSQL database"

      - alert: HighMemoryUsage
        expr: |
          (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is above 90%"

      - alert: SearchQueueBacklog
        expr: |
          celery_queue_length{queue="searches"} > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Search queue backlog"
          description: "More than 100 searches pending in queue"
```

### Alertmanager Configuration

```yaml
# alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: '${SLACK_WEBHOOK_URL}'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical'
      continue: true
    - match:
        severity: warning
      receiver: 'warning'

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: 'VinylDigger Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}'

  - name: 'critical'
    slack_configs:
      - channel: '#alerts-critical'
        title: '🚨 CRITICAL: VinylDigger Alert'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_SERVICE_KEY}'

  - name: 'warning'
    slack_configs:
      - channel: '#alerts-warning'
        title: '⚠️ Warning: VinylDigger Alert'
```

## Dashboards

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "VinylDigger Overview",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (method)"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=\"error\"}[5m])) / sum(rate(http_requests_total[5m]))"
          }
        ],
        "type": "stat"
      },
      {
        "title": "Response Time (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
          }
        ],
        "type": "gauge"
      },
      {
        "title": "Active Searches",
        "targets": [
          {
            "expr": "active_searches_total"
          }
        ],
        "type": "stat"
      },
      {
        "title": "Search Execution Time by Platform",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(search_execution_duration_seconds_bucket[5m])) by (le, platform))"
          }
        ],
        "type": "graph"
      },
      {
        "title": "External API Calls",
        "targets": [
          {
            "expr": "sum(rate(external_api_calls_total[5m])) by (service, status)"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Database Connections",
        "targets": [
          {
            "expr": "postgresql_connections_active"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Redis Memory Usage",
        "targets": [
          {
            "expr": "redis_memory_used_bytes / redis_memory_max_bytes"
          }
        ],
        "type": "gauge"
      }
    ]
  }
}
```

### Custom Business Dashboard

```python
# backend/src/api/v1/endpoints/metrics.py
from typing import Dict, Any
from datetime import datetime, timedelta

@router.get("/metrics/business")
async def get_business_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get business metrics for dashboard"""

    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # User metrics
    total_users = await db.scalar(
        select(func.count(User.id))
    )

    active_users_24h = await db.scalar(
        select(func.count(User.id))
        .where(User.last_login > last_24h)
    )

    # Search metrics
    total_searches = await db.scalar(
        select(func.count(SavedSearch.id))
        .where(SavedSearch.user_id == current_user.id)
    )

    active_searches = await db.scalar(
        select(func.count(SavedSearch.id))
        .where(
            SavedSearch.user_id == current_user.id,
            SavedSearch.is_active == True
        )
    )

    # Results metrics
    results_last_7d = await db.scalar(
        select(func.count(SearchResult.id))
        .join(SavedSearch)
        .where(
            SavedSearch.user_id == current_user.id,
            SearchResult.created_at > last_7d
        )
    )

    # Price analytics
    avg_price = await db.scalar(
        select(func.avg(SearchResult.price))
        .join(SavedSearch)
        .where(SavedSearch.user_id == current_user.id)
    )

    return {
        "users": {
            "total": total_users,
            "active_24h": active_users_24h
        },
        "searches": {
            "total": total_searches,
            "active": active_searches
        },
        "results": {
            "last_7_days": results_last_7d,
            "avg_price": float(avg_price or 0)
        },
        "timestamp": now.isoformat()
    }
```

## Performance Monitoring

### APM Integration

```python
# backend/src/core/apm.py
from elasticapm import Client
from elasticapm.contrib.starlette import ElasticAPM

def setup_apm(app, service_name: str = "vinyldigger-api"):
    """Setup Elastic APM"""

    apm_config = {
        'SERVICE_NAME': service_name,
        'SERVER_URL': settings.APM_SERVER_URL,
        'SECRET_TOKEN': settings.APM_SECRET_TOKEN,
        'ENVIRONMENT': settings.ENVIRONMENT,
        'CAPTURE_HEADERS': True,
        'CAPTURE_BODY': 'all',
        'TRANSACTION_SAMPLE_RATE': 0.1,  # Sample 10% of transactions
    }

    apm = ElasticAPM(app, Client(apm_config))
    return apm

# Custom transaction tracking
from elasticapm import async_capture_span

class SearchService:
    @async_capture_span()
    async def execute_search(self, search_id: int):
        # Search execution logic
        pass

    @async_capture_span()
    async def fetch_from_discogs(self, query: str):
        # Discogs API call
        pass
```

### Database Query Performance

```python
# Log slow queries with context
from sqlalchemy import event
from sqlalchemy.engine import Engine
import logging

slow_query_logger = logging.getLogger("slow_queries")

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_time = time.time() - context._query_start_time

    if total_time > 0.5:  # Log queries over 500ms
        slow_query_logger.warning(
            "slow_query",
            extra={
                "duration": total_time,
                "statement": statement,
                "parameters": parameters,
                "stack_trace": traceback.extract_stack()
            }
        )

# Query analysis endpoint
@router.get("/metrics/slow-queries")
async def get_slow_queries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # Get slow queries from pg_stat_statements
    result = await db.execute(
        text("""
            SELECT
                query,
                calls,
                mean_exec_time,
                total_exec_time,
                stddev_exec_time
            FROM pg_stat_statements
            WHERE mean_exec_time > 100  -- Over 100ms
            ORDER BY mean_exec_time DESC
            LIMIT 20
        """)
    )

    return [
        {
            "query": row.query,
            "calls": row.calls,
            "mean_time_ms": row.mean_exec_time,
            "total_time_ms": row.total_exec_time,
            "stddev_time_ms": row.stddev_exec_time
        }
        for row in result
    ]
```

## Security Monitoring

### Security Event Logging

```python
# backend/src/core/security_monitoring.py
import structlog
from typing import Optional
from datetime import datetime

security_logger = structlog.get_logger("security")

class SecurityMonitor:
    @staticmethod
    async def log_authentication_attempt(
        email: str,
        success: bool,
        ip_address: str,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None
    ):
        await security_logger.info(
            "authentication_attempt",
            event_type="auth",
            email=email,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason=failure_reason,
            timestamp=datetime.utcnow().isoformat()
        )

    @staticmethod
    async def log_authorization_failure(
        user_id: str,
        resource: str,
        action: str,
        ip_address: str
    ):
        await security_logger.warning(
            "authorization_failure",
            event_type="authz",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=ip_address,
            timestamp=datetime.utcnow().isoformat()
        )

    @staticmethod
    async def log_suspicious_activity(
        activity_type: str,
        details: dict,
        ip_address: str,
        user_id: Optional[str] = None
    ):
        await security_logger.error(
            "suspicious_activity",
            event_type="security",
            activity_type=activity_type,
            details=details,
            ip_address=ip_address,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat()
        )

# Integration with fail2ban
class Fail2BanLogger:
    @staticmethod
    def log_auth_failure(ip_address: str):
        # Log in format that fail2ban can parse
        with open("/var/log/vinyldigger/auth.log", "a") as f:
            f.write(
                f"{datetime.utcnow().strftime('%b %d %H:%M:%S')} "
                f"vinyldigger auth: Failed password for user from {ip_address}\n"
            )
```

### Security Metrics Dashboard

```python
# Security-specific Prometheus metrics
from prometheus_client import Counter, Gauge

auth_attempts = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['result', 'method']
)

failed_auth_by_ip = Counter(
    'failed_auth_by_ip_total',
    'Failed authentication attempts by IP',
    ['ip_address']
)

suspicious_activities = Counter(
    'suspicious_activities_total',
    'Suspicious activities detected',
    ['activity_type']
)

active_sessions = Gauge(
    'active_sessions_total',
    'Number of active user sessions'
)

# Track security events
async def track_auth_attempt(success: bool, method: str, ip_address: str):
    result = "success" if success else "failure"
    auth_attempts.labels(result=result, method=method).inc()

    if not success:
        failed_auth_by_ip.labels(ip_address=ip_address).inc()

async def track_suspicious_activity(activity_type: str):
    suspicious_activities.labels(activity_type=activity_type).inc()
```

## Monitoring Best Practices

### 1. Golden Signals
Monitor the four golden signals:
- **Latency**: Response time of requests
- **Traffic**: Request rate
- **Errors**: Error rate and types
- **Saturation**: Resource utilization

### 2. SLI/SLO Definition

```yaml
# Service Level Indicators and Objectives
slis:
  - name: api_availability
    description: "API endpoint availability"
    query: "sum(rate(http_requests_total[5m])) - sum(rate(http_requests_total{status=~'5..'}[5m]))"

  - name: api_latency_p99
    description: "99th percentile API latency"
    query: "histogram_quantile(0.99, http_request_duration_seconds_bucket)"

  - name: search_success_rate
    description: "Search execution success rate"
    query: "sum(rate(search_execution_total{status='success'}[5m])) / sum(rate(search_execution_total[5m]))"

slos:
  - sli: api_availability
    objective: 99.9
    window: 30d

  - sli: api_latency_p99
    objective: 500  # milliseconds
    window: 7d

  - sli: search_success_rate
    objective: 95
    window: 7d
```

### 3. Runbook Integration

```python
# Include runbook links in alerts
annotations:
  summary: "High error rate detected"
  description: "Error rate is above 5% for the last 5 minutes"
  runbook_url: "https://wiki.vinyldigger.com/runbooks/high-error-rate"
  dashboard_url: "https://grafana.vinyldigger.com/d/api-overview"
```

### 4. On-Call Setup

```yaml
# PagerDuty integration
pagerduty_configs:
  - service_key: '${PAGERDUTY_SERVICE_KEY}'
    description: '{{ .GroupLabels.alertname }}'
    details:
      firing: '{{ .Alerts.Firing | len }}'
      resolved: '{{ .Alerts.Resolved | len }}'
      alerts: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

## Monitoring Checklist

### Setup
- [ ] Structured logging configured
- [ ] Metrics collection enabled
- [ ] Distributed tracing implemented
- [ ] Health checks defined
- [ ] Alerting rules created
- [ ] Dashboards configured

### Operational
- [ ] Log aggregation working
- [ ] Metrics being collected
- [ ] Traces being captured
- [ ] Alerts firing correctly
- [ ] Dashboards accessible
- [ ] On-call rotation set up

### Security
- [ ] Security events logged
- [ ] Audit trail maintained
- [ ] Suspicious activity detection
- [ ] Compliance logging enabled

### Performance
- [ ] APM configured
- [ ] Slow query logging
- [ ] Resource monitoring
- [ ] SLI/SLO tracking
