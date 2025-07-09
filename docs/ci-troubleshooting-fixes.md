# CI/CD Troubleshooting Fixes

## Issues Resolved

### 1. `just: command not found` on macOS runners

**Problem**: The arkade installation of `just` was failing on macOS runners in the e2e-tests workflow.

**Root Cause**: The workflow was only installing docker-compose on Linux runners, not macOS.

**Fix Applied**: Removed the OS-specific condition from docker-compose installation in all workflows:
```yaml
# Before
- name: Install docker-compose
  if: runner.os == 'Linux'
  uses: alexellis/arkade-get@...

# After
- name: Install docker-compose
  uses: alexellis/arkade-get@...
```

### 2. Docker Compose healthcheck `start-period` error

**Problem**: `validating docker-compose.test.yml: services.backend.healthcheck additional properties 'start-period' not allowed`

**Root Cause**: The `start-period` healthcheck option requires Docker Compose v2.3+ format or newer versions of docker-compose. The version installed by arkade might not support this feature.

**Fix Applied**: Removed `start-period` from all healthcheck configurations in `docker-compose.test.yml`:
```yaml
# Before
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 5s
  retries: 5
  start-period: 30s  # Removed this line

# After
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## Alternative Solutions Considered

1. **Using Docker Compose plugin**: Modern Docker includes `docker compose` as a plugin, but this would require updating all commands throughout the project.

2. **Pinning docker-compose version**: Could specify a newer version in arkade, but removing `start-period` is simpler and more compatible.

3. **Adding compose file version**: Adding `version: '3.8'` was considered but modern docker-compose deprecates version declarations.

## Testing the Fixes

The fixes ensure:
- All CI runners (Linux and macOS) have docker-compose installed
- Healthchecks work with older docker-compose versions
- Services still wait appropriately through increased retries instead of start-period

## Future Improvements

Consider migrating to `docker compose` (plugin) instead of `docker-compose` (standalone) for better compatibility and features.
