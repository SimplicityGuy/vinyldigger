# VinylDigger Security Best Practices Guide

## Overview

This guide outlines security best practices for developing, deploying, and maintaining VinylDigger. It covers application security, infrastructure security, and operational security measures.

## Table of Contents

- [Application Security](#application-security)
- [Authentication & Authorization](#authentication--authorization)
- [Data Protection](#data-protection)
- [API Security](#api-security)
- [Infrastructure Security](#infrastructure-security)
- [Dependency Management](#dependency-management)
- [Security Monitoring](#security-monitoring)
- [Incident Response](#incident-response)

## Application Security

### Input Validation

All user input must be validated and sanitized:

```python
# Use Pydantic for automatic validation
from pydantic import BaseModel, EmailStr, validator
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    discogs_username: Optional[str] = None

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

    @validator('discogs_username')
    def validate_username(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, - and _')
        return v
```

### SQL Injection Prevention

Always use parameterized queries with SQLAlchemy:

```python
# NEVER do this
query = f"SELECT * FROM users WHERE email = '{email}'"

# ALWAYS do this
result = await db.execute(
    select(User).where(User.email == email)
)

# For raw SQL (if absolutely necessary)
result = await db.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": email}
)
```

### XSS Prevention

For the React frontend:

```typescript
// React automatically escapes values
const SafeComponent = ({ userContent }) => {
  return <div>{userContent}</div>; // Safe by default
};

// If you need HTML content, sanitize it first
import DOMPurify from 'dompurify';

const HtmlContent = ({ html }) => {
  const clean = DOMPurify.sanitize(html);
  return <div dangerouslySetInnerHTML={{ __html: clean }} />;
};
```

### CSRF Protection

Implement CSRF protection for state-changing operations:

```python
# backend/src/core/security.py
from fastapi import HTTPException, Request
import secrets

def generate_csrf_token():
    return secrets.token_urlsafe(32)

async def validate_csrf_token(request: Request, token: str):
    session_token = request.session.get("csrf_token")
    if not session_token or session_token != token:
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
```

## Authentication & Authorization

### Password Security

```python
# backend/src/core/security.py
from passlib.context import CryptContext

# Configure bcrypt with appropriate cost factor
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Adjust based on performance requirements
)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### JWT Security

```python
# Secure JWT configuration
from datetime import datetime, timedelta
from jose import jwt, JWTError

SECRET_KEY = settings.SECRET_KEY  # From environment, min 32 bytes
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(subject: str, expires_delta: timedelta = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode = {
        "exp": expire,
        "sub": subject,
        "type": "access",
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16)  # Unique token ID
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Token validation with all claims
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Validate token type
        if payload.get("type") not in ["access", "refresh"]:
            raise ValueError("Invalid token type")
        return payload
    except JWTError:
        raise ValueError("Invalid token")
```

### Role-Based Access Control (RBAC)

```python
from enum import Enum
from functools import wraps

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

def require_role(allowed_roles: list[UserRole]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@router.delete("/users/{user_id}")
@require_role([UserRole.ADMIN])
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    # Only admins can delete users
    pass
```

## Data Protection

### API Key Encryption

```python
from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

# Generate encryption key
def generate_encryption_key():
    return Fernet.generate_key().decode()

# Store encrypted API keys
async def store_api_key(user_id: str, service: str, api_key: str):
    encrypted_key = encryption_service.encrypt(api_key)

    db_api_key = APIKey(
        user_id=user_id,
        service=service,
        encrypted_key=encrypted_key,
        key_hash=hashlib.sha256(api_key.encode()).hexdigest()[:16]
    )
    db.add(db_api_key)
    await db.commit()
```

### Sensitive Data Handling

```python
# Never log sensitive data
import logging
from typing import Any, Dict

class SanitizingFilter(logging.Filter):
    """Remove sensitive data from logs"""

    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret',
        'authorization', 'cookie', 'session'
    }

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'args'):
            record.args = self._sanitize(record.args)
        return True

    def _sanitize(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: '***REDACTED***' if k.lower() in self.SENSITIVE_FIELDS else self._sanitize(v)
                for k, v in data.items()
            }
        elif isinstance(data, (list, tuple)):
            return [self._sanitize(item) for item in data]
        return data
```

### Database Security

```python
# Use environment-specific database credentials
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Ensure SSL for production databases
if os.environ.get("ENVIRONMENT") == "production":
    DATABASE_URL += "?sslmode=require"

# Row-level security
class SecureQuery:
    """Ensure users can only access their own data"""

    @staticmethod
    def user_searches(db: AsyncSession, user_id: str):
        return select(SavedSearch).where(
            SavedSearch.user_id == user_id,
            SavedSearch.is_deleted == False
        )

    @staticmethod
    def user_can_access_search(db: AsyncSession, user_id: str, search_id: int):
        result = await db.execute(
            select(SavedSearch).where(
                SavedSearch.id == search_id,
                SavedSearch.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None
```

## API Security

### Rate Limiting

```python
from fastapi import Request, HTTPException
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
        self.clients = defaultdict(list)

    async def check_rate_limit(self, request: Request):
        client_ip = request.client.host
        now = time.time()

        # Clean old requests
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if req_time > now - self.window
        ]

        if len(self.clients[client_ip]) >= self.requests:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )

        self.clients[client_ip].append(now)

# Apply rate limiting
rate_limiter = RateLimiter(requests=100, window=60)  # 100 requests per minute

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    await rate_limiter.check_rate_limit(request)
    response = await call_next(request)
    return response
```

### API Versioning & Deprecation

```python
from fastapi import Header, HTTPException
import warnings

async def check_api_version(
    x_api_version: str = Header(None),
    accept: str = Header(None)
):
    # Support version in Accept header
    if accept and "version=" in accept:
        version = accept.split("version=")[1].split(";")[0]
    else:
        version = x_api_version or "1"

    if version == "1":
        warnings.warn("API v1 is deprecated, please upgrade to v2")
    elif version not in ["1", "2"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported API version: {version}"
        )

    return version
```

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

# Strict CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vinyldigger.com",
        "https://www.vinyldigger.com"
    ] if settings.ENVIRONMENT == "production" else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=86400,  # 24 hours
)
```

## Infrastructure Security

### Docker Security

```dockerfile
# Use specific versions, not latest
FROM python:3.13-slim-bookworm

# Run as non-root user
RUN useradd -m -u 1000 appuser

# Set security labels
LABEL security.scan="true" \
      security.vulnerability.product="vinyldigger" \
      security.vulnerability.version="${VERSION}"

# Copy only necessary files
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()"
```

### Environment Variables

```bash
# .env.production
# Use strong, unique values
SECRET_KEY=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Database security
DATABASE_URL=postgresql://user:pass@localhost:5432/vinyldigger?sslmode=require
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=0

# Security headers
SECURE_HEADERS_ENABLED=true
HSTS_MAX_AGE=31536000
```

### Network Security

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    networks:
      - backend
      - frontend
    expose:
      - "8000"  # Don't publish ports directly

  postgres:
    networks:
      - backend
    # No ports exposed to host

  redis:
    networks:
      - backend
    # No ports exposed to host

  nginx:
    networks:
      - frontend
    ports:
      - "443:443"  # Only expose HTTPS
    volumes:
      - ./ssl:/etc/nginx/ssl:ro

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access
```

## Dependency Management

### Automated Vulnerability Scanning

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  python-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Bandit Security Scan
        uses: gaurav-nelson/bandit-action@v1
        with:
          path: "backend/"
          level: "medium"

      - name: Run Safety Check
        run: |
          pip install safety
          safety check --json

  docker-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'

  npm-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run npm audit
        run: |
          cd frontend
          npm audit --audit-level=moderate
```

### Dependency Updates

```toml
# pyproject.toml
[tool.dependabot]
package-ecosystem = "pip"
directory = "/"
schedule = "weekly"
open-pull-requests-limit = 10

[tool.poetry.dependencies]
# Pin major versions, allow minor updates
fastapi = "^0.115.0"
sqlalchemy = "^2.0.0"
pydantic = "^2.10.0"
```

## Security Monitoring

### Logging Security Events

```python
import structlog
from datetime import datetime

security_logger = structlog.get_logger("security")

class SecurityEventLogger:
    @staticmethod
    async def log_login_attempt(email: str, success: bool, ip: str):
        await security_logger.info(
            "login_attempt",
            email=email,
            success=success,
            ip=ip,
            timestamp=datetime.utcnow().isoformat()
        )

    @staticmethod
    async def log_permission_denied(user_id: str, resource: str, action: str):
        await security_logger.warning(
            "permission_denied",
            user_id=user_id,
            resource=resource,
            action=action,
            timestamp=datetime.utcnow().isoformat()
        )

    @staticmethod
    async def log_suspicious_activity(user_id: str, activity: str, details: dict):
        await security_logger.error(
            "suspicious_activity",
            user_id=user_id,
            activity=activity,
            details=details,
            timestamp=datetime.utcnow().isoformat()
        )
```

### Intrusion Detection

```python
class IntrusionDetector:
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.suspicious_patterns = [
            r'(?i)(union|select|insert|update|delete|drop)\s',
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]

    async def check_request(self, request: Request):
        # Check for SQL injection patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, str(request.url)):
                await SecurityEventLogger.log_suspicious_activity(
                    user_id="anonymous",
                    activity="sql_injection_attempt",
                    details={"url": str(request.url)}
                )
                raise HTTPException(status_code=400)

        # Check for brute force
        client_ip = request.client.host
        if len(self.failed_attempts[client_ip]) > 5:
            await SecurityEventLogger.log_suspicious_activity(
                user_id="anonymous",
                activity="brute_force_attempt",
                details={"ip": client_ip}
            )
            raise HTTPException(status_code=429)
```

## Incident Response

### Response Plan

1. **Detection**
   - Monitor security logs
   - Set up alerts for suspicious activities
   - Regular security scans

2. **Containment**
   - Isolate affected systems
   - Revoke compromised credentials
   - Block malicious IPs

3. **Eradication**
   - Remove malicious code
   - Patch vulnerabilities
   - Update security measures

4. **Recovery**
   - Restore from clean backups
   - Verify system integrity
   - Monitor for persistence

5. **Lessons Learned**
   - Document incident
   - Update security procedures
   - Implement preventive measures

### Emergency Procedures

```bash
#!/bin/bash
# emergency-shutdown.sh

# Shut down all services
docker-compose down

# Revoke all JWT tokens
redis-cli FLUSHDB

# Backup database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Rotate secrets
python -c "import secrets; print(f'NEW_SECRET_KEY={secrets.token_urlsafe(32)}')" >> .env.new

# Alert team
curl -X POST $SLACK_WEBHOOK -d '{"text": "SECURITY ALERT: Emergency shutdown initiated"}'
```

## Security Checklist

### Development
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] XSS prevention measures
- [ ] CSRF tokens implemented
- [ ] Sensitive data encryption
- [ ] Secure password hashing
- [ ] JWT properly configured
- [ ] Rate limiting active

### Deployment
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] Secrets in environment variables
- [ ] Database SSL enabled
- [ ] Non-root containers
- [ ] Network segmentation
- [ ] Firewall rules configured

### Operations
- [ ] Security logging enabled
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Incident response plan
- [ ] Regular security scans
- [ ] Dependency updates automated
- [ ] Access logs reviewed
- [ ] Penetration testing scheduled

## Compliance Considerations

### GDPR Compliance
- User data export functionality
- Right to deletion implementation
- Privacy policy and consent
- Data minimization practices

### Security Standards
- OWASP Top 10 mitigation
- CWE/SANS Top 25 prevention
- PCI DSS compliance (if handling payments)
- SOC 2 readiness

## Resources

- [OWASP Security Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Python Security](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)
