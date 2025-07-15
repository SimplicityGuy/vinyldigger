# OAuth Authentication Fixes Documentation

## Overview

This document describes the recent critical fixes implemented for eBay OAuth authentication and background task scheduling in VinylDigger.

## Critical Issues Fixed

### 1. eBay API 401 Unauthorized Errors

**Problem**: Worker service was receiving `401 Unauthorized` errors when making eBay API calls, causing search tasks to fail.

**Root Cause**: Environment mismatch between credentials and API endpoints:
- App configuration stored `PRODUCTION` environment
- But consumer key contained `SBX` (sandbox) identifier
- Service was using production URLs with sandbox credentials

**Solution**: Enhanced `EbayService` with automatic environment detection:

```python
async def _determine_environment(self, db: AsyncSession) -> bool:
    """Determine if we should use sandbox based on app config."""
    # Auto-detect environment from App ID
    is_sandbox = False
    if "SBX" in app_config.consumer_key.upper():
        is_sandbox = True
    elif "PRD" in app_config.consumer_key.upper():
        is_sandbox = False
    else:
        # Fall back to the configured environment
        is_sandbox = app_config.environment == OAuthEnvironment.SANDBOX

    return is_sandbox
```

**Key Features**:
- Automatic sandbox/production detection from App ID patterns
- Dynamic base URL switching during service initialization
- Backward compatibility with explicit environment configuration
- Proper OAuth scope selection based on environment

### 2. Scheduler Timezone Issues

**Problem**: Background search scheduler was crashing with timezone-related errors.

**Root Cause**: Mixing timezone-naive and timezone-aware datetime objects:
```python
# OLD: timezone-naive datetime
now = datetime.utcnow()

# NEW: timezone-aware datetime
now = datetime.now(timezone.utc)
```

**Solution**: Updated scheduler to use consistent timezone-aware datetimes throughout.

### 3. OAuth Token Field Length Constraints

**Problem**: Database errors when storing large OAuth tokens (tokens exceeded 500 character limit).

**Solution**: Increased OAuth token field lengths from 500 to 5000 characters:
- `access_token`: String(5000)
- `access_token_secret`: String(5000)
- `refresh_token`: String(5000)

## Implementation Details

### Environment Detection Logic

The service now follows this priority order for environment detection:

1. **Explicit Configuration**: If `use_sandbox` parameter is provided, use that
2. **App ID Pattern Matching**: Check for `SBX` or `PRD` in consumer key
3. **Database Configuration**: Fall back to `app_config.environment` setting
4. **Default**: Production environment if no indicators found

### Dynamic Service Reconfiguration

The `EbayService` can now update its configuration at runtime:

```python
async def _update_base_url_if_needed(self, db: AsyncSession) -> None:
    """Update base URL if environment wasn't explicitly set."""
    if self.use_sandbox is None:
        is_sandbox = await self._determine_environment(db)
        new_base_url = self.SANDBOX_URL if is_sandbox else self.PRODUCTION_URL

        if new_base_url != self.base_url:
            self.base_url = new_base_url
            # Recreate HTTP client with new base URL
            await self._recreate_client()
```

### Backward Compatibility

All changes maintain backward compatibility:
- Existing OAuth tokens continue to work
- Manual environment configuration still supported
- Legacy app configurations work without changes

## Testing Results

### Before Fixes
```
worker-1  | [2025-07-12 22:45:31,584: INFO/ForkPoolWorker-2] HTTP Request: GET https://api.ebay.com/buy/browse/v1/item_summary/search?q=solarstone&limit=50&offset=0&filter=categoryIds%3A%7B176985%7D "HTTP/1.1 401 Unauthorized"
worker-1  | [2025-07-12 22:45:31,585: ERROR/ForkPoolWorker-2] eBay API search error: Client error '401 Unauthorized'
```

### After Fixes
```
worker-1  | [2025-07-12 22:52:51,747: INFO/ForkPoolWorker-2] Updated eBay service to use sandbox environment
worker-1  | [2025-07-12 22:52:52,257: INFO/ForkPoolWorker-2] HTTP Request: GET https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search?q=solarstone&limit=50&offset=0&filter=categoryIds%3A%7B176985%7D "HTTP/1.1 200 OK"
worker-1  | [2025-07-12 22:52:52,267: INFO/ForkPoolWorker-2] Search e8454c11-01da-4a65-87ed-5e84746d616f completed successfully. Added 0 new results.
```

## Configuration Guide

### For Sandbox Development

1. Create eBay Sandbox app at [developer.ebay.com](https://developer.ebay.com)
2. Get Sandbox App ID (contains `SBX`, e.g., `YourName-App-SBX-12345-abcdef`)
3. Enter credentials in VinylDigger admin panel
4. Service automatically detects sandbox environment

### For Production Use

1. Create eBay Production app at [developer.ebay.com](https://developer.ebay.com)
2. Get Production App ID (contains `PRD`, e.g., `YourName-App-PRD-12345-abcdef`)
3. Enter credentials in VinylDigger admin panel
4. Service automatically detects production environment

### Manual Environment Override

If needed, you can still manually specify environment:

```python
# Force sandbox
async with EbayService(use_sandbox=True) as service:
    results = await service.search(query, filters, db, user_id)

# Force production
async with EbayService(use_sandbox=False) as service:
    results = await service.search(query, filters, db, user_id)
```

## Database Migration

The OAuth token field expansion was handled via Alembic migration:

```sql
-- Increase token field lengths to accommodate larger tokens
ALTER TABLE oauth_tokens
ALTER COLUMN access_token TYPE VARCHAR(5000),
ALTER COLUMN access_token_secret TYPE VARCHAR(5000),
ALTER COLUMN refresh_token TYPE VARCHAR(5000);
```

## Monitoring and Logging

Enhanced logging provides better visibility into OAuth authentication:

- Environment detection decisions are logged
- Base URL changes are logged with environment names
- Authentication failures include more context
- Token retrieval and validation results are tracked

## Future Enhancements

### Token Refresh Handling
```python
# TODO: Implement automatic token refresh
async def _refresh_token_if_needed(self, token: OAuthToken) -> str:
    if self._is_token_expired(token):
        return await self._refresh_access_token(token)
    return token.access_token
```

### Rate Limiting
Consider implementing eBay API rate limiting to prevent quota exhaustion:
```python
# TODO: Add rate limiting for eBay API calls
async def _rate_limited_request(self, method: str, url: str, **kwargs):
    await self._wait_for_rate_limit()
    return await self.client.request(method, url, **kwargs)
```

## Security Considerations

1. **Environment Isolation**: Sandbox and production credentials are kept separate
2. **Token Encryption**: OAuth tokens remain encrypted in database storage
3. **Scope Management**: Different OAuth scopes used for sandbox vs production
4. **State Validation**: CSRF protection maintained throughout OAuth flow

## Related Documentation

- [eBay Developer Setup Guide](./ebay-developer-setup.md)
- [OAuth Setup Guide](../oauth-setup.md)
- [Troubleshooting Guide](../troubleshooting.md)
- [Testing Guide](./testing-guide.md)
