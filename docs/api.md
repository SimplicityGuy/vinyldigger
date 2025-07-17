# VinylDigger API Documentation

*Last updated: July 2025*

## Overview

VinylDigger provides a RESTful API for automating vinyl record discovery across Discogs and eBay. The API is built with FastAPI and automatically generates OpenAPI/Swagger documentation.

### API Features

- **Enhanced User Management**: New PUT endpoint for updating user profile information
- **Complete Search CRUD**: Full create, read, update, delete operations for saved searches
- **Improved Response Models**: Enhanced user response including creation and update timestamps
- **Better Error Handling**: More descriptive error responses for validation failures
- **Extended Field Support**: Additional search configuration options for better personalization

### Base URLs
- **API Base**: `/api/v1`
- **Health Check**: `/health`
- **Interactive Documentation**: `/api/docs` (Swagger UI)
- **ReDoc Documentation**: `/api/redoc`
- **OpenAPI Schema**: `/api/openapi.json`

### Authentication

All endpoints except authentication endpoints and health check require JWT authentication.

**Authorization Header Format**:
```
Authorization: Bearer <access_token>
```

## Data Types

### Recommendation Types

The API returns recommendation types in user-friendly format:

| API Response | Internal Value | Description |
|--------------|----------------|-------------|
| `"BEST PRICE"` | `BEST_PRICE` | Single item with best price+shipping |
| `"MULTI ITEM DEAL"` | `MULTI_ITEM_DEAL` | Seller with multiple wantlist items |
| `"CONDITION VALUE"` | `CONDITION_VALUE` | Better condition at slight price premium |
| `"LOCATION PREFERENCE"` | `LOCATION_PREFERENCE` | Preferred seller location |
| `"HIGH FEEDBACK"` | `HIGH_FEEDBACK` | Seller with excellent reputation |

**Note**: API responses use space-separated format for better readability, while internal code uses underscore format for consistency.

## Authentication Endpoints

### Register New User
Creates a new user account.

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com"
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
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Update Current User
Updates the authenticated user's profile information.

```http
PUT /api/v1/auth/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "newemail@example.com"
}
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newemail@example.com",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:45:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Email already registered by another user
- `401 Unauthorized`: Invalid or missing authentication token

## OAuth Endpoints

### Check OAuth Status
Check if the user has authorized the application for a specific provider.

```http
GET /api/v1/oauth/status/{provider}
Authorization: Bearer <access_token>
```

**Path Parameters**:
- `provider`: `discogs` or `ebay`

**Response**:
```json
{
  "provider": "discogs",
  "is_configured": true,
  "is_authorized": true,
  "username": "vinylcollector123"
}
```

### Initiate OAuth Authorization
Start the OAuth flow to authorize access to a provider.

```http
GET /api/v1/oauth/authorize/{provider}
Authorization: Bearer <access_token>
```

**Path Parameters**:
- `provider`: `discogs` or `ebay`

**Response**: Redirects to the provider's authorization page

### OAuth Callback
Handles the OAuth callback after user authorizes access.

```http
GET /api/v1/oauth/callback/{provider}?oauth_token=...&oauth_verifier=...
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `oauth_token`: Token from provider
- `oauth_verifier`: Verifier from provider

**Response**:
```json
{
  "message": "Discogs authorization successful",
  "username": "vinylcollector123"
}
```

### Revoke OAuth Access
Revoke access tokens for a specific provider.

```http
DELETE /api/v1/oauth/revoke/{provider}
Authorization: Bearer <access_token>
```

**Path Parameters**:
- `provider`: `discogs` or `ebay`

**Response**:
```json
{
  "message": "Discogs access revoked successfully"
}
```

## Admin Endpoints

Admin endpoints require admin privileges (email ending in @admin.com or @vinyldigger.com).

### Get OAuth App Configuration
List all configured OAuth applications.

```http
GET /api/v1/admin/app-config
Authorization: Bearer <admin_access_token>
```

**Response**:
```json
[
  {
    "provider": "DISCOGS",
    "consumer_key": "abc123...",
    "callback_url": "https://yourdomain.com/oauth/callback/discogs",
    "is_configured": true
  }
]
```

### Create/Update OAuth App Configuration
Configure OAuth application credentials.

```http
POST /api/v1/admin/app-config
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
  "provider": "DISCOGS",
  "consumer_key": "your_consumer_key",
  "consumer_secret": "your_consumer_secret",
  "callback_url": "https://yourdomain.com/oauth/callback/discogs"
}
```

**Response**:
```json
{
  "provider": "DISCOGS",
  "consumer_key": "your_consumer_key",
  "is_configured": true
}
```

### Delete OAuth App Configuration
Remove OAuth application configuration.

```http
DELETE /api/v1/admin/app-config/{provider}
Authorization: Bearer <admin_access_token>
```

**Path Parameters**:
- `provider`: `DISCOGS` or `EBAY`

**Response**:
```json
{
  "message": "App configuration deleted successfully"
}
```

## Configuration Endpoints

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

### Update Saved Search
Updates an existing saved search's parameters.

```http
PUT /api/v1/searches/{search_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Updated Jazz Vinyl Search",
  "query": "blue note jazz vinyl rare",
  "platform": "discogs",
  "check_interval_hours": 12,
  "min_record_condition": "NM",
  "min_sleeve_condition": "VG+",
  "seller_location_preference": "EU"
}
```

**Path Parameters**:
- `search_id`: UUID of the search

**Request Body**: All fields are optional. Only provided fields will be updated.

**Response**: Updated search object (same format as create response)

**Error Responses**:
- `404 Not Found`: Search not found or doesn't belong to authenticated user
- `400 Bad Request`: Invalid request parameters

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

### Sync Collection and Want List
Triggers synchronization with both user's Discogs collection and want list.

```http
POST /api/v1/collections/sync
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "message": "Collection and want list sync queued successfully"
}
```

### Sync Collection Only
Triggers synchronization with user's Discogs collection only.

```http
POST /api/v1/collections/sync/collection
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "message": "Collection sync queued successfully"
}
```

### Sync Want List Only
Triggers synchronization with user's Discogs want list only.

```http
POST /api/v1/collections/sync/wantlist
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "message": "Want list sync queued successfully"
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
- **400 Bad Request**: Invalid request data (e.g., email already registered)
- **401 Unauthorized**: Missing or invalid authentication token
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error in request body
- **500 Internal Server Error**: Server error (check logs for details)

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

Currently, the API does not implement rate limiting internally. However, external API rate limits apply:
- Discogs: 60 requests per minute
- eBay: 5000 requests per day

Future versions will implement:
- Per-user rate limiting (100 requests/minute)
- Endpoint-specific limits
- Rate limit headers (X-RateLimit-*)

## Pagination

Current implementation:
- Search results: Limited to 100 items per request
- Collections: No pagination (full sync)

Planned improvements:
- Cursor-based pagination for all list endpoints
- Configurable page sizes (10-100 items)
- Total count headers
- Link headers for navigation

Example (future):
```
GET /api/v1/searches?cursor=eyJpZCI6MTIzfQ&limit=20
```

## Webhooks

Webhook support is planned for real-time notifications:

Planned events:
- `search.completed` - When a search finishes
- `analysis.ready` - When analysis is available
- `deal.found` - When new deals are discovered
- `sync.completed` - When collection sync finishes

Future webhook format:
```json
{
  "event": "search.completed",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "search_id": "uuid",
    "results_count": 42
  }
}

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

## Search Analysis Endpoints

### Get Search Analysis
Retrieves comprehensive analysis for a search including seller recommendations and deal scores.

```http
GET /api/v1/analysis/search/{search_id}/analysis
Authorization: Bearer <access_token>
```

**Path Parameters**:
- `search_id`: UUID of the search to analyze

**Response**:
```json
{
  "search_id": "550e8400-e29b-41d4-a716-446655440000",
  "analysis_completed": true,
  "analysis": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "total_results": 45,
    "total_sellers": 12,
    "multi_item_sellers": 5,
    "min_price": 25.00,
    "max_price": 125.00,
    "avg_price": 68.50,
    "wantlist_matches": 18,
    "collection_duplicates": 3,
    "new_discoveries": 24,
    "completed_at": "2024-01-20T15:30:00Z"
  },
  "recommendations": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "type": "MULTI ITEM DEAL",
      "deal_score": "EXCELLENT",
      "score_value": 92.5,
      "title": "Great Multi-Item Deal",
      "description": "Save significantly on shipping costs",
      "recommendation_reason": "Buy 4 items together to save $35 on shipping",
      "total_items": 4,
      "wantlist_items": 3,
      "total_value": 180.00,
      "estimated_shipping": 15.00,
      "total_cost": 195.00,
      "potential_savings": 35.00,
      "seller": {
        "id": "880e8400-e29b-41d4-a716-446655440003",
        "name": "VinylEmporium",
        "location": "Los Angeles, CA",
        "feedback_score": 98.5
      },
      "item_ids": ["item1", "item2", "item3", "item4"]
    }
  ],
  "seller_analyses": [
    {
      "rank": 1,
      "total_items": 4,
      "wantlist_items": 3,
      "total_value": 180.00,
      "estimated_shipping": 15.00,
      "overall_score": 88.5,
      "price_competitiveness": 85.0,
      "inventory_depth_score": 90.0,
      "seller_reputation_score": 95.0,
      "location_preference_score": 100.0,
      "seller": {
        "id": "880e8400-e29b-41d4-a716-446655440003",
        "name": "VinylEmporium",
        "location": "Los Angeles, CA",
        "country_code": "US",
        "feedback_score": 98.5,
        "total_feedback_count": 1247
      }
    }
  ]
}
```

**When analysis not completed**:
```json
{
  "search_id": "550e8400-e29b-41d4-a716-446655440000",
  "analysis_completed": false,
  "message": "Analysis not yet completed for this search"
}
```

### Get Multi-Item Deals
Retrieves sellers with multiple items for potential shipping savings.

```http
GET /api/v1/analysis/search/{search_id}/multi-item-deals
Authorization: Bearer <access_token>
```

**Path Parameters**:
- `search_id`: UUID of the search

**Response**:
```json
{
  "search_id": "550e8400-e29b-41d4-a716-446655440000",
  "multi_item_deals": [
    {
      "seller": {
        "id": "880e8400-e29b-41d4-a716-446655440003",
        "name": "VinylEmporium",
        "location": "Los Angeles, CA",
        "feedback_score": 98.5
      },
      "total_items": 4,
      "wantlist_items": 3,
      "total_value": 180.00,
      "estimated_shipping": 15.00,
      "total_cost": 195.00,
      "potential_savings": 35.00,
      "deal_score": "EXCELLENT",
      "item_ids": ["item1", "item2", "item3", "item4"]
    }
  ]
}
```

### Get Price Comparison
Retrieves price comparison data across platforms and sellers for matching items.

```http
GET /api/v1/analysis/search/{search_id}/price-comparison
Authorization: Bearer <access_token>
```

**Path Parameters**:
- `search_id`: UUID of the search

**Response**:
```json
{
  "search_id": "550e8400-e29b-41d4-a716-446655440000",
  "price_comparisons": [
    {
      "item_match": {
        "id": "990e8400-e29b-41d4-a716-446655440004",
        "canonical_title": "Kind of Blue",
        "canonical_artist": "Miles Davis",
        "total_matches": 3
      },
      "listings": [
        {
          "id": "aa0e8400-e29b-41d4-a716-446655440005",
          "platform": "DISCOGS",
          "price": 45.00,
          "condition": "VG+",
          "seller": {
            "id": "bb0e8400-e29b-41d4-a716-446655440006",
            "name": "JazzCollector99",
            "location": "New York, NY",
            "feedback_score": 99.2
          },
          "is_in_wantlist": true,
          "is_in_collection": false
        },
        {
          "id": "cc0e8400-e29b-41d4-a716-446655440007",
          "platform": "EBAY",
          "price": 52.00,
          "condition": "NM",
          "seller": {
            "id": "dd0e8400-e29b-41d4-a716-446655440008",
            "name": "vintagevinyl_shop",
            "location": "Chicago, IL",
            "feedback_score": 97.8
          },
          "is_in_wantlist": true,
          "is_in_collection": false
        }
      ]
    }
  ]
}
```

## Examples

### Complete Authentication Flow

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Register
response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
    "email": "collector@example.com",
    "password": "secure123"
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

### Creating and Running a Search with Analysis

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

// Wait for analysis to complete (in practice, check periodically)
await new Promise(resolve => setTimeout(resolve, 30000));

// Get comprehensive analysis
const analysis = await fetch(`${API_URL}/analysis/search/${search.id}/analysis`, {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
}).then(res => res.json());

console.log(`Analysis completed: ${analysis.analysis_completed}`);
console.log(`Found ${analysis.analysis?.total_results || 0} items from ${analysis.analysis?.total_sellers || 0} sellers`);
console.log(`${analysis.recommendations?.length || 0} deal recommendations found`);

// Get multi-item deals specifically
const deals = await fetch(`${API_URL}/analysis/search/${search.id}/multi-item-deals`, {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
}).then(res => res.json());

console.log(`${deals.multi_item_deals.length} multi-item deals available`);

// Get price comparisons
const priceComparison = await fetch(`${API_URL}/analysis/search/${search.id}/price-comparison`, {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
}).then(res => res.json());

console.log(`Price comparisons for ${priceComparison.price_comparisons.length} unique items`);
```

## Related Documentation

- **[API Client Examples](api-examples.md)** - Example code in Python, JavaScript/TypeScript, Go, and cURL
- **[Architecture Guide](architecture.md)** - Understanding the system architecture and data flow
- **[OAuth Setup Guide](oauth-setup.md)** - Setting up OAuth authentication for Discogs and eBay
- **[Analysis Engine Guide](analysis-engine.md)** - Detailed explanation of the AI-powered analysis system
- **[Security Guide](security.md)** - Security implementation details and best practices
- **[Testing Guide](testing.md)** - How to test API integrations and endpoints
- **[Troubleshooting Guide](troubleshooting.md)** - Common API issues and solutions
- **[Deployment Guide](deployment.md)** - Production deployment considerations for the API
