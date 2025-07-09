# VinylDigger API Documentation

## Overview

VinylDigger provides a RESTful API for automating vinyl record discovery across Discogs and eBay. The API is built with FastAPI and automatically generates OpenAPI/Swagger documentation.

### Base URLs
- **API Base**: `/api/v1`
- **Health Check**: `/health`
- **Interactive Documentation**: `/api/docs` (Swagger UI)
- **OpenAPI Schema**: `/api/openapi.json`

### Authentication

All endpoints except authentication endpoints and health check require JWT authentication.

**Authorization Header Format**:
```
Authorization: Bearer <access_token>
```

## Authentication Endpoints

### Register New User
Creates a new user account.

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123",
  "discogs_username": "optional_username"
}
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "discogs_username": "optional_username"
}
```

### Login
Authenticates a user and returns JWT tokens.

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Refresh Token
Obtains a new access token using a refresh token.

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**: Same as login response

### Get Current User
Returns information about the authenticated user.

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "discogs_username": "optional_username"
}
```

## Configuration Endpoints

### Update/Create API Key
Stores encrypted API credentials for external services.

```http
PUT /api/v1/config/api-keys
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service": "discogs",
  "key": "your_consumer_key",
  "secret": "your_consumer_secret"
}
```

**Supported Services**: `discogs`, `ebay`

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "service": "discogs",
  "created_at": "2024-01-20T10:30:00Z"
}
```

### Get All API Keys
Lists all configured API keys (without exposing the actual keys).

```http
GET /api/v1/config/api-keys
Authorization: Bearer <access_token>
```

**Response**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "service": "discogs",
    "created_at": "2024-01-20T10:30:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "service": "ebay",
    "created_at": "2024-01-20T11:00:00Z"
  }
]
```

### Delete API Key
Removes stored API credentials for a service.

```http
DELETE /api/v1/config/api-keys/{service}
Authorization: Bearer <access_token>
```

**Path Parameters**:
- `service`: `discogs` or `ebay`

**Response**:
```json
{
  "message": "API key deleted successfully"
}
```

### Get User Preferences
Retrieves user's search and notification preferences.

```http
GET /api/v1/config/preferences
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "min_record_condition": "VG+",
  "min_sleeve_condition": "VG+",
  "seller_location_preference": "US",
  "check_interval_hours": 24
}
```

### Update User Preferences
Updates user's search and notification preferences.

```http
PUT /api/v1/config/preferences
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "min_record_condition": "NM",
  "min_sleeve_condition": "VG+",
  "seller_location_preference": "worldwide",
  "check_interval_hours": 12
}
```

**All fields are optional**. Only provided fields will be updated.

## Search Endpoints

### Create Saved Search
Creates a new search that will run periodically.

```http
POST /api/v1/searches
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Jazz Vinyl Search",
  "query": "blue note jazz vinyl",
  "platform": "both",
  "filters": {
    "min_year": 1950,
    "max_year": 1970
  },
  "check_interval_hours": 24
}
```

**Platform Options**: `ebay`, `discogs`, `both`

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Jazz Vinyl Search",
  "query": "blue note jazz vinyl",
  "platform": "both",
  "filters": {
    "min_year": 1950,
    "max_year": 1970
  },
  "is_active": true,
  "check_interval_hours": 24,
  "last_checked_at": null
}
```

### Get All Saved Searches
Lists all searches for the authenticated user.

```http
GET /api/v1/searches
Authorization: Bearer <access_token>
```

**Response**: Array of search objects (same format as create response)

### Get Specific Search
Retrieves details of a specific search.

```http
GET /api/v1/searches/{search_id}
Authorization: Bearer <access_token>
```

**Path Parameters**:
- `search_id`: UUID of the search

### Delete Search
Removes a saved search and its results.

```http
DELETE /api/v1/searches/{search_id}
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "message": "Search deleted successfully"
}
```

### Run Search Manually
Triggers immediate execution of a search.

```http
POST /api/v1/searches/{search_id}/run
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "message": "Search queued successfully"
}
```

### Get Search Results
Retrieves the most recent results for a search.

```http
GET /api/v1/searches/{search_id}/results
Authorization: Bearer <access_token>
```

**Response**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "platform": "ebay",
    "item_id": "123456789",
    "item_data": {
      "title": "Blue Note 1568 Horace Silver Blowin' The Blues Away",
      "price": 45.00,
      "currency": "USD",
      "condition": "VG+/VG+",
      "seller": "vinylcollector123",
      "url": "https://www.ebay.com/itm/123456789"
    },
    "is_in_collection": false,
    "is_in_wantlist": true,
    "created_at": "2024-01-20T15:30:00Z"
  }
]
```

**Note**: Returns up to 100 most recent results

## Collection Endpoints

### Sync Collection
Triggers synchronization with user's Discogs collection.

```http
POST /api/v1/collections/sync
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "message": "Collection sync queued successfully"
}
```

### Get Collection Status
Returns information about the user's synced collection.

```http
GET /api/v1/collections/status
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "item_count": 523,
  "last_sync_at": "2024-01-20T10:00:00Z"
}
```

### Get Want List Status
Returns information about the user's synced want list.

```http
GET /api/v1/collections/wantlist/status
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "item_count": 47,
  "last_sync_at": "2024-01-20T10:05:00Z"
}
```

## Health Check

### System Health
Checks if the API is running and healthy.

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy"
}
```

## Error Responses

All endpoints use consistent error response format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

- **200 OK**: Successful request
- **201 Created**: Resource successfully created
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

### Validation Errors

For requests with invalid data, the API returns detailed validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "invalid email address",
      "type": "value_error.email"
    }
  ]
}
```

## Rate Limiting

Currently, the API does not implement rate limiting. This may be added in future versions.

## Pagination

Search results are limited to 100 items. Full pagination support is planned for future releases.

## Webhooks

Webhook support for real-time notifications is planned for future releases.

## SDK and Client Libraries

Official client libraries are planned for:
- Python
- JavaScript/TypeScript
- Go

## API Versioning

The API uses URL versioning. The current version is `v1`. When breaking changes are introduced, a new version will be created while maintaining the previous version for backward compatibility.

## Security Notes

1. **API Keys**: All external API keys are encrypted using Fernet symmetric encryption before storage
2. **JWT Tokens**: Access tokens expire after 30 minutes, refresh tokens after 7 days
3. **HTTPS**: Always use HTTPS in production
4. **CORS**: Configure CORS appropriately for your frontend domain

## Examples

### Complete Authentication Flow

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Register
response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
    "email": "collector@example.com",
    "password": "secure123",
    "discogs_username": "vinyl_lover"
})
user = response.json()

# 2. Login
response = requests.post(f"{BASE_URL}/api/v1/auth/login", data={
    "username": "collector@example.com",
    "password": "secure123"
})
tokens = response.json()
access_token = tokens["access_token"]

# 3. Use API with token
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
print(response.json())
```

### Creating and Running a Search

```javascript
const API_URL = 'http://localhost:8000/api/v1';

// Create a search
const search = await fetch(`${API_URL}/searches`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Rare Jazz Vinyl',
    query: 'blue note liberty',
    platform: 'both',
    check_interval_hours: 12
  })
}).then(res => res.json());

// Run the search immediately
await fetch(`${API_URL}/searches/${search.id}/run`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

// Check results after some time
const results = await fetch(`${API_URL}/searches/${search.id}/results`, {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
}).then(res => res.json());

console.log(`Found ${results.length} items`);
```
