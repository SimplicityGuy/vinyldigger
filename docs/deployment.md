# VinylDigger Deployment Guide

*Last updated: July 2025*

## Overview

This guide covers deploying VinylDigger to production environments. The application is containerized and can be deployed to any platform that supports Docker.

## Prerequisites

- Docker and Docker Compose installed
- Domain name with DNS configured
- SSL certificate (or use Let's Encrypt)
- PostgreSQL database (or use containerized version)
- Redis instance (or use containerized version)

## Environment Configuration

### Required Environment Variables

Create a `.env.production` file with the following variables:

```bash
# Security
SECRET_KEY=your-very-secure-secret-key-here
ENCRYPTION_KEY=your-fernet-encryption-key-here

# Database
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/vinyldigger

# Redis
REDIS_URL=redis://redis:6379/0

# API Configuration
API_BASE_URL=https://api.yourdomain.com
FRONTEND_URL=https://yourdomain.com

# CORS Origins (comma-separated)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Optional: Email configuration (future feature)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@yourdomain.com
SMTP_PASSWORD=your-smtp-password

# Optional: Monitoring
SENTRY_DSN=your-sentry-dsn-if-using-sentry

# Scheduler Configuration
TZ=America/Los_Angeles  # Set your timezone for accurate scheduling
SCHEDULER_TIMEZONE=America/Los_Angeles  # Must match TZ
```

### Generating Secure Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY (Fernet key)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Deployment Options

### Option 1: Docker Compose (Recommended for Single Server)

1. **Prepare the server**:
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Docker
   curl -fsSL https://get.docker.com | sh

   # Install Docker Compose
   sudo apt install docker-compose
   ```

2. **Clone the repository**:
   ```bash
   git clone https://github.com/SimplicityGuy/vinyldigger.git
   cd vinyldigger
   ```

3. **Configure environment**:
   ```bash
   cp backend/.env.example backend/.env.production
   # Edit backend/.env.production with your values
   ```

4. **Build and start services**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Database Setup and Migrations**:

   **Important**: VinylDigger supports OAuth tokens up to 5000 characters. The database schema includes:
   - `discogs_oauth_token` and `ebay_oauth_token` columns with VARCHAR(5000)
   - Automatic migration on backend startup if migration files exist

   **For new deployments**:
   ```bash
   # The backend will automatically run migrations on startup
   # Check migration status
   docker-compose -f docker-compose.prod.yml exec backend alembic current

   # If you need to create a new migration
   docker-compose -f docker-compose.prod.yml exec backend alembic revision --autogenerate -m "Your migration description"
   docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
   ```

   **Database Requirements**:
   - PostgreSQL 16+ recommended
   - Minimum 2GB RAM for database server
   - SSD storage recommended for performance
   - Regular backups essential (see Backup Strategy section)

### Option 2: Kubernetes Deployment

1. **Create ConfigMap for environment variables**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: vinyldigger-config
   data:
     API_BASE_URL: "https://api.yourdomain.com"
     FRONTEND_URL: "https://yourdomain.com"
     CORS_ORIGINS: "https://yourdomain.com"
   ```

2. **Create Secret for sensitive data**:
   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: vinyldigger-secrets
   type: Opaque
   stringData:
     SECRET_KEY: "your-secret-key"
     ENCRYPTION_KEY: "your-encryption-key"
     DATABASE_URL: "postgresql+asyncpg://user:pass@host/db"
   ```

3. **Deploy services**: See `k8s/` directory for complete manifests

### Option 3: Cloud Platform Deployment

#### AWS ECS

1. **Build and push images to ECR**:
   ```bash
   aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY

   docker build -t vinyldigger-backend ./backend
   docker tag vinyldigger-backend:latest $ECR_REGISTRY/vinyldigger-backend:latest
   docker push $ECR_REGISTRY/vinyldigger-backend:latest
   ```

2. **Create ECS task definitions** for each service
3. **Configure Application Load Balancer** for routing
4. **Set up RDS PostgreSQL** and ElastiCache Redis

#### Google Cloud Run

1. **Build and push to Container Registry**:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/vinyldigger-backend ./backend
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy vinyldigger-backend \
     --image gcr.io/PROJECT_ID/vinyldigger-backend \
     --platform managed \
     --region us-central1 \
     --set-env-vars "DATABASE_URL=$DATABASE_URL"
   ```

#### Heroku

1. **Create Heroku apps**:
   ```bash
   heroku create vinyldigger-api
   heroku create vinyldigger-frontend
   ```

2. **Add buildpacks**:
   ```bash
   heroku buildpacks:add --index 1 heroku/python -a vinyldigger-api
   heroku buildpacks:add --index 1 heroku/nodejs -a vinyldigger-frontend
   ```

3. **Deploy**:
   ```bash
   git push heroku main
   ```

## Docker Image Standards

### Building Production Images

**Always use the provided build script for OCI-compliant images:**

```bash
# Build all images with proper OCI labels
./scripts/docker-build.sh

# Build specific service
./scripts/docker-build.sh backend
./scripts/docker-build.sh frontend
```

### OCI Labels Compliance

All VinylDigger Docker images implement [OCI standard labels](https://github.com/opencontainers/image-spec/blob/main/annotations.md) for better traceability and compliance:

- Images include metadata like version, git commit SHA, build date
- Validation is enforced with hadolint in CI/CD pipeline
- Labels enable proper image tracking in registries
- See [Docker OCI Labels Documentation](docker-oci-labels.md) for details

### Security Best Practices

- **Non-root users**: Backend runs as `appuser`, frontend as `nginx` user
- **Pinned base images**: All base images use specific versions
- **Multi-stage builds**: Minimizes final image size and attack surface
- **Health checks**: All services include health check endpoints
- **Hadolint validation**: Dockerfile best practices enforced

## Production Configuration

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' https://api.yourdomain.com" always;

    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Database Configuration

#### PostgreSQL Optimization

```sql
-- Recommended PostgreSQL settings for production
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';
```

#### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Run daily via cron
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
DB_NAME="vinyldigger"

# Create backup
pg_dump -h localhost -U postgres -d $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/backup_$DATE.sql.gz s3://your-backup-bucket/postgres/
```

### Redis Configuration

```conf
# redis.conf additions for production
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Monitoring and Logging

### Health Checks

```yaml
# docker-compose.prod.yml health checks
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Log Aggregation

Configure Docker to send logs to a centralized service:

```json
{
  "log-driver": "syslog",
  "log-opts": {
    "syslog-address": "udp://logs.example.com:514",
    "syslog-format": "rfc5424",
    "tag": "vinyldigger/{{.Name}}"
  }
}
```

### Application Monitoring

1. **Prometheus Metrics** (future):
   ```python
   # Add to FastAPI app
   from prometheus_fastapi_instrumentator import Instrumentator

   Instrumentator().instrument(app).expose(app)
   ```

2. **Sentry Error Tracking**:
   ```python
   import sentry_sdk
   from sentry_sdk.integrations.fastapi import FastApiIntegration

   sentry_sdk.init(
       dsn=settings.SENTRY_DSN,
       integrations=[FastApiIntegration()],
       environment="production"
   )
   ```

## SSL/TLS Configuration

### Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificates
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Auto-renewal (add to crontab)
0 0,12 * * * /usr/bin/certbot renew --quiet
```

### SSL Security Configuration

```nginx
# Strong SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_stapling on;
ssl_stapling_verify on;
```

## Performance Tuning

### Backend Optimization

1. **Gunicorn Configuration**:
   ```python
   # gunicorn.conf.py
   bind = "0.0.0.0:8000"
   workers = 4  # 2 * CPU cores + 1
   worker_class = "uvicorn.workers.UvicornWorker"
   worker_connections = 1000
   max_requests = 1000
   max_requests_jitter = 50
   preload_app = True
   ```

2. **Database Connection Pooling**:
   ```python
   # In database.py
   engine = create_async_engine(
       settings.DATABASE_URL,
       pool_size=20,
       max_overflow=40,
       pool_pre_ping=True,
       pool_recycle=3600,
       echo=False  # Set to True for SQL debugging in development only
   )
   ```

### Frontend Optimization

1. **Build Optimization**:
   ```bash
   # Production build
   npm run build

   # Analyze bundle size
   npm run build -- --analyze
   ```

2. **CDN Configuration**:
   - Serve static assets from CDN
   - Enable gzip compression
   - Set appropriate cache headers

## Security Hardening

### System Security

```bash
# Firewall configuration
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# Fail2ban for SSH protection
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### Application Security

1. **Rate Limiting**:
   ```python
   from slowapi import Limiter

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```

2. **Security Headers**: See Nginx configuration above

## Backup and Recovery

### Automated Backups

```yaml
# docker-compose.prod.yml
services:
  postgres-backup:
    image: prodrigestivill/postgres-backup-local
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=vinyldigger
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - SCHEDULE=@daily
      - BACKUP_KEEP_DAYS=7
      - BACKUP_KEEP_WEEKS=4
      - BACKUP_KEEP_MONTHS=6
    volumes:
      - ./backups:/backups
```

### Disaster Recovery Plan

1. **Database Recovery**:
   ```bash
   # Restore from backup
   gunzip < backup_20240120_120000.sql.gz | psql -h localhost -U postgres -d vinyldigger
   ```

2. **Application Recovery**:
   - Keep infrastructure as code
   - Document all configuration
   - Test recovery procedures regularly

## Maintenance

### Zero-Downtime Deployments

```bash
#!/bin/bash
# deploy.sh - Blue-green deployment

# Pull latest code
git pull origin main

# Build new images with OCI labels
./scripts/docker-build.sh

# Run any new migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Start new containers
docker-compose -f docker-compose.prod.yml up -d --scale backend=2

# Wait for health checks
echo "Waiting for health checks..."
sleep 30

# Verify new containers are healthy
docker-compose -f docker-compose.prod.yml ps

# Scale back to single instance
docker-compose -f docker-compose.prod.yml up -d --scale backend=1

# Cleanup old images
docker system prune -f
```

### Regular Maintenance Tasks

1. **Database Maintenance**:
   ```sql
   -- Run weekly
   VACUUM ANALYZE;
   REINDEX DATABASE vinyldigger;
   ```

2. **Log Rotation**:
   ```bash
   # /etc/logrotate.d/vinyldigger
   /var/log/vinyldigger/*.log {
       daily
       rotate 14
       compress
       delaycompress
       notifempty
       create 0640 www-data www-data
       sharedscripts
   }
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Check DATABASE_URL format (must use `postgresql+asyncpg://`)
   - Verify PostgreSQL is running and accessible
   - Check firewall rules and security groups
   - Ensure database has proper OAuth token column sizes (VARCHAR(5000))

2. **Redis Connection Errors**:
   - Verify Redis is running (`redis-cli ping`)
   - Check REDIS_URL format
   - Monitor memory usage (`redis-cli info memory`)
   - For Python 3.13: Type annotation issues are already fixed

3. **Worker Not Processing Tasks**:
   - Check Celery logs: `docker-compose logs worker`
   - Verify Redis connectivity from worker container
   - Monitor queue depth: `docker-compose exec worker celery -A src.workers.celery_app inspect active`
   - Check for task failures: `docker-compose exec worker celery -A src.workers.celery_app inspect stats`

4. **Scheduler Issues**:
   - Verify timezone settings (TZ and SCHEDULER_TIMEZONE must match)
   - Check scheduler logs: `docker-compose logs scheduler`
   - Ensure APScheduler is running: look for "Scheduler started" in logs
   - For timezone issues: Set both TZ and SCHEDULER_TIMEZONE environment variables

5. **OAuth Token Storage Errors**:
   - Database must support 5000-character OAuth tokens
   - Run migrations to update column sizes if needed
   - Check for truncation errors in logs

### Debug Mode

Enable debug logging in production (temporarily):

```bash
# Set environment variable
DEBUG=true docker-compose -f docker-compose.prod.yml up
```

## Cost Optimization

1. **Resource Right-sizing**:
   - Monitor actual usage
   - Adjust container limits
   - Use spot instances where appropriate

2. **Caching Strategy**:
   - Enable CloudFlare or similar CDN
   - Configure browser caching
   - Use Redis for application caching

3. **Database Optimization**:
   - Regular VACUUM and ANALYZE
   - Appropriate indexes
   - Query optimization
