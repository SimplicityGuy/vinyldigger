# VinylDigger API Client Examples

*Last updated: July 2025*

## Overview

This guide provides example code for interacting with the VinylDigger API in multiple programming languages. Each example demonstrates authentication, basic operations, and error handling.

## Table of Contents

- [Python](#python)
- [JavaScript/TypeScript](#javascripttypescript)
- [Go](#go)
- [cURL](#curl)
- [Postman Collection](#postman-collection)

## Base Configuration

```yaml
# API Configuration
base_url: https://api.vinyldigger.com/api/v1
auth_endpoints:
  register: /auth/register
  login: /auth/login
  refresh: /auth/refresh
  me: /auth/me
```

## Python

### Installation

```bash
pip install requests python-jose
```

### Complete Python Client

```python
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

class VinylDiggerClient:
    """Python client for VinylDigger API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = f"{base_url}/api/v1"
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request"""
        # Auto-refresh token if needed
        if self.access_token and self._should_refresh_token():
            self.refresh_access_token()

        # Add auth header if we have a token
        if self.access_token:
            self.session.headers["Authorization"] = f"Bearer {self.access_token}"

        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)

        if response.status_code == 401 and self.refresh_token:
            # Try refreshing token and retry
            self.refresh_access_token()
            response = self.session.request(method, url, **kwargs)

        response.raise_for_status()
        return response.json() if response.content else {}

    def _should_refresh_token(self) -> bool:
        """Check if token should be refreshed"""
        if not self.token_expires:
            return False
        return datetime.utcnow() >= self.token_expires - timedelta(minutes=5)

    # Authentication Methods

    def register(self, email: str, password: str) -> Dict[str, Any]:
        """Register new user"""
        data = {
            "email": email,
            "password": password
        }
        return self._request("POST", "/auth/register", json=data)

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login and store tokens"""
        data = {
            "username": email,  # API uses username field for email
            "password": password
        }
        response = self._request("POST", "/auth/login", data=data)

        self.access_token = response["access_token"]
        self.refresh_token = response["refresh_token"]
        self.token_expires = datetime.utcnow() + timedelta(minutes=30)

        return response

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        response = self._request("POST", "/auth/refresh", json={
            "refresh_token": self.refresh_token
        })

        self.access_token = response["access_token"]
        self.refresh_token = response["refresh_token"]
        self.token_expires = datetime.utcnow() + timedelta(minutes=30)

        return response

    def get_current_user(self) -> Dict[str, Any]:
        """Get current user information"""
        return self._request("GET", "/auth/me")

    # OAuth Management

    def get_oauth_status(self, provider: str) -> Dict[str, Any]:
        """Check OAuth authorization status for a provider"""
        return self._request("GET", f"/oauth/status/{provider}")

    def initiate_oauth(self, provider: str) -> str:
        """Get OAuth authorization URL"""
        response = self._request("GET", f"/oauth/authorize/{provider}", allow_redirects=False)
        return response.headers.get("Location")

    def revoke_oauth(self, provider: str) -> None:
        """Revoke OAuth access for a provider"""
        self._request("DELETE", f"/oauth/revoke/{provider}")

    # Search Management

    def create_search(self,
                     name: str,
                     search_type: str = "all",
                     artist: Optional[str] = None,
                     album: Optional[str] = None,
                     min_condition: Optional[str] = None,
                     max_price: Optional[float] = None,
                     **kwargs) -> Dict[str, Any]:
        """Create a new saved search"""
        data = {
            "name": name,
            "search_type": search_type,
            "search_params": {
                "artist": artist,
                "album": album,
                "min_condition": min_condition,
                "max_price": max_price,
                **kwargs
            },
            "is_active": True
        }
        return self._request("POST", "/searches", json=data)

    def get_searches(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get all saved searches"""
        params = {"active_only": active_only} if active_only else {}
        return self._request("GET", "/searches", params=params)

    def get_search(self, search_id: int) -> Dict[str, Any]:
        """Get specific search"""
        return self._request("GET", f"/searches/{search_id}")

    def update_search(self, search_id: int, **updates) -> Dict[str, Any]:
        """Update search parameters"""
        return self._request("PUT", f"/searches/{search_id}", json=updates)

    def delete_search(self, search_id: int) -> None:
        """Delete a search"""
        self._request("DELETE", f"/searches/{search_id}")

    def execute_search(self, search_id: int) -> Dict[str, Any]:
        """Manually trigger search execution"""
        return self._request("POST", f"/searches/{search_id}/execute")

    def get_search_results(self, search_id: int,
                          skip: int = 0,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """Get search results with pagination"""
        params = {"skip": skip, "limit": limit}
        return self._request("GET", f"/searches/{search_id}/results", params=params)

    # Collection Management

    def sync_collection_and_wantlist(self) -> Dict[str, Any]:
        """Sync both Discogs collection and want list"""
        return self._request("POST", "/collections/sync")

    def sync_collection_only(self) -> Dict[str, Any]:
        """Sync Discogs collection only"""
        return self._request("POST", "/collections/sync/collection")

    def sync_wantlist_only(self) -> Dict[str, Any]:
        """Sync Discogs want list only"""
        return self._request("POST", "/collections/sync/wantlist")

    def get_collection_status(self) -> Dict[str, Any]:
        """Get collection status"""
        return self._request("GET", "/collections/status")

    def get_wantlist_status(self) -> Dict[str, Any]:
        """Get want list status"""
        return self._request("GET", "/wantlist/status")

# Example Usage
if __name__ == "__main__":
    # Initialize client
    client = VinylDiggerClient("http://localhost:8000")

    # Register new user
    try:
        user = client.register("collector@example.com", "SecurePass123!")
        print(f"Registered user: {user['email']}")
    except requests.HTTPError as e:
        if e.response.status_code == 400:
            print("User already exists")

    # Login
    client.login("collector@example.com", "SecurePass123!")
    print("Logged in successfully")

    # Check OAuth status
    discogs_status = client.get_oauth_status("discogs")
    print(f"Discogs authorized: {discogs_status['is_authorized']}")

    # Initiate OAuth if not authorized
    if not discogs_status['is_authorized']:
        auth_url = client.initiate_oauth("discogs")
        print(f"Please authorize at: {auth_url}")

    # Create a search
    search = client.create_search(
        name="Pink Floyd First Pressings",
        search_type="vinyl",
        artist="Pink Floyd",
        min_condition="VG",
        max_price=100.00,
        pressing="first",
        location="US"
    )
    print(f"Created search: {search['name']} (ID: {search['id']})")

    # Execute search manually
    result = client.execute_search(search['id'])
    print(f"Search executing, task ID: {result['task_id']}")

    # Get results
    import time
    time.sleep(30)  # Wait for search to complete

    results = client.get_search_results(search['id'])
    print(f"Found {len(results)} results")

    for item in results[:5]:
        print(f"- {item['title']} - ${item['price']} ({item['condition']})")
```

## JavaScript/TypeScript

### Installation

```bash
npm install axios
# For TypeScript
npm install --save-dev @types/node
```

### TypeScript Client

```typescript
import axios, { AxiosInstance, AxiosError } from 'axios';

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface User {
  id: string;
  email: string;
}

interface SavedSearch {
  id: number;
  name: string;
  search_type: string;
  search_params: Record<string, any>;
  is_active: boolean;
  created_at: string;
  next_run_at?: string;
}

interface SearchResult {
  id: number;
  title: string;
  artist: string;
  price: number;
  condition: string;
  location: string;
  seller: string;
  url: string;
  platform: string;
}

class VinylDiggerClient {
  private api: AxiosInstance;
  private accessToken?: string;
  private refreshToken?: string;
  private tokenExpiry?: Date;

  constructor(baseURL: string = 'http://localhost:8000') {
    this.api = axios.create({
      baseURL: `${baseURL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for auth
    this.api.interceptors.request.use(
      async (config) => {
        if (this.accessToken) {
          // Check if token needs refresh
          if (this.shouldRefreshToken()) {
            await this.refreshAccessToken();
          }
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor for token refresh
    this.api.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && this.refreshToken && originalRequest) {
          await this.refreshAccessToken();
          return this.api(originalRequest);
        }

        return Promise.reject(error);
      }
    );
  }

  private shouldRefreshToken(): boolean {
    if (!this.tokenExpiry) return false;
    const now = new Date();
    const fiveMinutesFromNow = new Date(now.getTime() + 5 * 60 * 1000);
    return this.tokenExpiry <= fiveMinutesFromNow;
  }

  // Authentication methods

  async register(email: string, password: string): Promise<User> {
    const response = await this.api.post<User>('/auth/register', {
      email,
      password,
    });
    return response.data;
  }

  async login(email: string, password: string): Promise<AuthTokens> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await this.api.post<AuthTokens>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    this.accessToken = response.data.access_token;
    this.refreshToken = response.data.refresh_token;
    this.tokenExpiry = new Date(Date.now() + 30 * 60 * 1000); // 30 minutes

    return response.data;
  }

  async refreshAccessToken(): Promise<void> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await this.api.post<AuthTokens>('/auth/refresh', {
      refresh_token: this.refreshToken,
    });

    this.accessToken = response.data.access_token;
    this.refreshToken = response.data.refresh_token;
    this.tokenExpiry = new Date(Date.now() + 30 * 60 * 1000);
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.api.get<User>('/auth/me');
    return response.data;
  }

  // OAuth management

  async getOAuthStatus(provider: 'discogs' | 'ebay'): Promise<{
    provider: string;
    is_configured: boolean;
    is_authorized: boolean;
    username?: string;
  }> {
    const response = await this.api.get(`/oauth/status/${provider}`);
    return response.data;
  }

  async initiateOAuth(provider: 'discogs' | 'ebay'): Promise<string> {
    try {
      await this.api.get(`/oauth/authorize/${provider}`, {
        maxRedirects: 0,
      });
    } catch (error: any) {
      if (error.response?.status === 302) {
        return error.response.headers.location;
      }
      throw error;
    }
    return '';
  }

  async revokeOAuth(provider: 'discogs' | 'ebay'): Promise<void> {
    await this.api.delete(`/oauth/revoke/${provider}`);
  }

  // Search management

  async createSearch(params: {
    name: string;
    search_type?: string;
    artist?: string;
    album?: string;
    min_condition?: string;
    max_price?: number;
    [key: string]: any;
  }): Promise<SavedSearch> {
    const { name, search_type = 'all', ...searchParams } = params;

    const response = await this.api.post<SavedSearch>('/searches', {
      name,
      search_type,
      search_params: searchParams,
      is_active: true,
    });

    return response.data;
  }

  async getSearches(activeOnly: boolean = false): Promise<SavedSearch[]> {
    const response = await this.api.get<SavedSearch[]>('/searches', {
      params: activeOnly ? { active_only: true } : {},
    });
    return response.data;
  }

  async getSearchResults(
    searchId: number,
    skip: number = 0,
    limit: number = 100
  ): Promise<SearchResult[]> {
    const response = await this.api.get<SearchResult[]>(
      `/searches/${searchId}/results`,
      { params: { skip, limit } }
    );
    return response.data;
  }

  async executeSearch(searchId: number): Promise<{ task_id: string }> {
    const response = await this.api.post<{ task_id: string }>(
      `/searches/${searchId}/execute`
    );
    return response.data;
  }
}

// Example usage
async function main() {
  const client = new VinylDiggerClient();

  try {
    // Register or login
    try {
      await client.register('collector@example.com', 'SecurePass123!');
      console.log('User registered');
    } catch (error) {
      console.log('User exists, logging in...');
    }

    await client.login('collector@example.com', 'SecurePass123!');
    console.log('Logged in successfully');

    // Check OAuth status and authorize if needed
    const discogsStatus = await client.getOAuthStatus('discogs');
    console.log('Discogs authorized:', discogsStatus.is_authorized);

    if (!discogsStatus.is_authorized) {
      const authUrl = await client.initiateOAuth('discogs');
      console.log('Please authorize at:', authUrl);
    }

    // Create a search
    const search = await client.createSearch({
      name: 'Rare Jazz Vinyl',
      search_type: 'vinyl',
      artist: 'Miles Davis',
      min_condition: 'VG+',
      max_price: 200,
    });
    console.log(`Created search: ${search.name}`);

    // Execute search
    const { task_id } = await client.executeSearch(search.id);
    console.log(`Search executing, task ID: ${task_id}`);

    // Wait and get results
    await new Promise(resolve => setTimeout(resolve, 30000));

    const results = await client.getSearchResults(search.id);
    console.log(`Found ${results.length} results`);

    results.slice(0, 5).forEach(item => {
      console.log(`- ${item.title} - $${item.price} (${item.condition})`);
    });

  } catch (error) {
    console.error('Error:', error);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

export default VinylDiggerClient;
```

## Go

### Installation

```bash
go get github.com/go-resty/resty/v2
```

### Go Client

```go
package vinyldigger

import (
    "encoding/json"
    "fmt"
    "time"

    "github.com/go-resty/resty/v2"
)

type Client struct {
    baseURL      string
    client       *resty.Client
    accessToken  string
    refreshToken string
    tokenExpiry  time.Time
}

type AuthTokens struct {
    AccessToken  string `json:"access_token"`
    RefreshToken string `json:"refresh_token"`
    TokenType    string `json:"token_type"`
}

type User struct {
    ID    string `json:"id"`
    Email string `json:"email"`
}

type SavedSearch struct {
    ID           int                    `json:"id"`
    Name         string                 `json:"name"`
    SearchType   string                 `json:"search_type"`
    SearchParams map[string]interface{} `json:"search_params"`
    IsActive     bool                   `json:"is_active"`
    CreatedAt    string                 `json:"created_at"`
    NextRunAt    *string                `json:"next_run_at,omitempty"`
}

type SearchResult struct {
    ID        int     `json:"id"`
    Title     string  `json:"title"`
    Artist    string  `json:"artist"`
    Price     float64 `json:"price"`
    Condition string  `json:"condition"`
    Location  string  `json:"location"`
    Seller    string  `json:"seller"`
    URL       string  `json:"url"`
    Platform  string  `json:"platform"`
}

// NewClient creates a new VinylDigger API client
func NewClient(baseURL string) *Client {
    if baseURL == "" {
        baseURL = "http://localhost:8000"
    }

    return &Client{
        baseURL: baseURL + "/api/v1",
        client:  resty.New(),
    }
}

// shouldRefreshToken checks if token needs refresh
func (c *Client) shouldRefreshToken() bool {
    if c.tokenExpiry.IsZero() {
        return false
    }
    return time.Until(c.tokenExpiry) < 5*time.Minute
}

// setAuthHeader sets the authorization header
func (c *Client) setAuthHeader(r *resty.Request) *resty.Request {
    if c.accessToken != "" {
        if c.shouldRefreshToken() {
            c.RefreshAccessToken()
        }
        r.SetAuthToken(c.accessToken)
    }
    return r
}

// Register creates a new user account
func (c *Client) Register(email, password string) (*User, error) {
    var user User

    body := map[string]interface{}{
        "email":    email,
        "password": password,
    }

    resp, err := c.client.R().
        SetBody(body).
        SetResult(&user).
        Post(c.baseURL + "/auth/register")

    if err != nil {
        return nil, err
    }
    if resp.IsError() {
        return nil, fmt.Errorf("registration failed: %s", resp.Status())
    }

    return &user, nil
}

// Login authenticates and stores tokens
func (c *Client) Login(email, password string) error {
    var tokens AuthTokens

    resp, err := c.client.R().
        SetFormData(map[string]string{
            "username": email,
            "password": password,
        }).
        SetResult(&tokens).
        Post(c.baseURL + "/auth/login")

    if err != nil {
        return err
    }
    if resp.IsError() {
        return fmt.Errorf("login failed: %s", resp.Status())
    }

    c.accessToken = tokens.AccessToken
    c.refreshToken = tokens.RefreshToken
    c.tokenExpiry = time.Now().Add(30 * time.Minute)

    return nil
}

// RefreshAccessToken refreshes the access token
func (c *Client) RefreshAccessToken() error {
    if c.refreshToken == "" {
        return fmt.Errorf("no refresh token available")
    }

    var tokens AuthTokens

    resp, err := c.client.R().
        SetBody(map[string]string{
            "refresh_token": c.refreshToken,
        }).
        SetResult(&tokens).
        Post(c.baseURL + "/auth/refresh")

    if err != nil {
        return err
    }
    if resp.IsError() {
        return fmt.Errorf("token refresh failed: %s", resp.Status())
    }

    c.accessToken = tokens.AccessToken
    c.refreshToken = tokens.RefreshToken
    c.tokenExpiry = time.Now().Add(30 * time.Minute)

    return nil
}

// GetCurrentUser gets the current user information
func (c *Client) GetCurrentUser() (*User, error) {
    var user User

    resp, err := c.setAuthHeader(c.client.R()).
        SetResult(&user).
        Get(c.baseURL + "/auth/me")

    if err != nil {
        return nil, err
    }
    if resp.IsError() {
        return nil, fmt.Errorf("failed to get user: %s", resp.Status())
    }

    return &user, nil
}

// OAuthStatus represents OAuth authorization status
type OAuthStatus struct {
    Provider      string  `json:"provider"`
    IsConfigured  bool    `json:"is_configured"`
    IsAuthorized  bool    `json:"is_authorized"`
    Username      *string `json:"username,omitempty"`
}

// GetOAuthStatus checks OAuth authorization status
func (c *Client) GetOAuthStatus(provider string) (*OAuthStatus, error) {
    var status OAuthStatus

    resp, err := c.setAuthHeader(c.client.R()).
        SetResult(&status).
        Get(c.baseURL + "/oauth/status/" + provider)

    if err != nil {
        return nil, err
    }
    if resp.IsError() {
        return nil, fmt.Errorf("failed to get OAuth status: %s", resp.Status())
    }

    return &status, nil
}

// InitiateOAuth starts OAuth authorization flow
func (c *Client) InitiateOAuth(provider string) (string, error) {
    resp, err := c.setAuthHeader(c.client.R()).
        SetDoNotParseResponse(true).
        Get(c.baseURL + "/oauth/authorize/" + provider)

    if err != nil {
        return "", err
    }

    location := resp.Header().Get("Location")
    if location == "" {
        return "", fmt.Errorf("no redirect URL returned")
    }

    return location, nil
}

// CreateSearch creates a new saved search
func (c *Client) CreateSearch(name string, params map[string]interface{}) (*SavedSearch, error) {
    var search SavedSearch

    searchType := "all"
    if st, ok := params["search_type"].(string); ok {
        searchType = st
        delete(params, "search_type")
    }

    body := map[string]interface{}{
        "name":          name,
        "search_type":   searchType,
        "search_params": params,
        "is_active":     true,
    }

    resp, err := c.setAuthHeader(c.client.R()).
        SetBody(body).
        SetResult(&search).
        Post(c.baseURL + "/searches")

    if err != nil {
        return nil, err
    }
    if resp.IsError() {
        return nil, fmt.Errorf("failed to create search: %s", resp.Status())
    }

    return &search, nil
}

// GetSearchResults gets paginated search results
func (c *Client) GetSearchResults(searchID, skip, limit int) ([]SearchResult, error) {
    var results []SearchResult

    resp, err := c.setAuthHeader(c.client.R()).
        SetQueryParams(map[string]string{
            "skip":  fmt.Sprintf("%d", skip),
            "limit": fmt.Sprintf("%d", limit),
        }).
        SetResult(&results).
        Get(fmt.Sprintf("%s/searches/%d/results", c.baseURL, searchID))

    if err != nil {
        return nil, err
    }
    if resp.IsError() {
        return nil, fmt.Errorf("failed to get results: %s", resp.Status())
    }

    return results, nil
}

// Example usage
func Example() {
    client := NewClient("http://localhost:8000")

    // Register or login
    _, err := client.Register("collector@example.com", "SecurePass123!")
    if err != nil {
        fmt.Println("User exists, logging in...")
    }

    err = client.Login("collector@example.com", "SecurePass123!")
    if err != nil {
        panic(err)
    }
    fmt.Println("Logged in successfully")

    // Check OAuth status
    status, err := client.GetOAuthStatus("discogs")
    if err != nil {
        panic(err)
    }

    if !status.IsAuthorized {
        authURL, err := client.InitiateOAuth("discogs")
        if err != nil {
            panic(err)
        }
        fmt.Printf("Please authorize at: %s\n", authURL)
    } else {
        fmt.Printf("Already authorized as: %s\n", *status.Username)
    }

    // Create search
    search, err := client.CreateSearch("Rare Vinyl", map[string]interface{}{
        "artist":        "Led Zeppelin",
        "min_condition": "VG",
        "max_price":     150.0,
    })
    if err != nil {
        panic(err)
    }
    fmt.Printf("Created search: %s (ID: %d)\n", search.Name, search.ID)

    // Get results
    results, err := client.GetSearchResults(search.ID, 0, 10)
    if err != nil {
        panic(err)
    }

    for _, item := range results {
        fmt.Printf("- %s - $%.2f (%s)\n", item.Title, item.Price, item.Condition)
    }
}
```

## cURL

### Basic cURL Examples

```bash
# Set variables
BASE_URL="http://localhost:8000/api/v1"
EMAIL="collector@example.com"
PASSWORD="SecurePass123!"

# Register new user
curl -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'",
    "password": "'"$PASSWORD"'"
  }'

# Login and save tokens
RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=$PASSWORD")

ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $RESPONSE | jq -r '.refresh_token')

# Get current user
curl -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Check OAuth status
curl -X GET "$BASE_URL/oauth/status/discogs" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Initiate OAuth authorization (returns redirect URL)
curl -X GET "$BASE_URL/oauth/authorize/discogs" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -w "%{redirect_url}\n" \
  --max-redirs 0

# Revoke OAuth access
curl -X DELETE "$BASE_URL/oauth/revoke/discogs" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Create a search
SEARCH_RESPONSE=$(curl -s -X POST "$BASE_URL/searches" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Beatles First Pressings",
    "search_type": "vinyl",
    "search_params": {
      "artist": "The Beatles",
      "min_condition": "VG",
      "max_price": 200,
      "pressing": "first"
    },
    "is_active": true
  }')

SEARCH_ID=$(echo $SEARCH_RESPONSE | jq -r '.id')

# Execute search manually
curl -X POST "$BASE_URL/searches/$SEARCH_ID/execute" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Get search results
curl -X GET "$BASE_URL/searches/$SEARCH_ID/results?skip=0&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Refresh token
NEW_TOKENS=$(curl -s -X POST "$BASE_URL/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "'"$REFRESH_TOKEN"'"}')

ACCESS_TOKEN=$(echo $NEW_TOKENS | jq -r '.access_token')
REFRESH_TOKEN=$(echo $NEW_TOKENS | jq -r '.refresh_token')
```

### Advanced cURL Script

```bash
#!/bin/bash
# vinyldigger-api.sh - VinylDigger API wrapper script

set -e

# Configuration
BASE_URL="${VINYL_DIGGER_URL:-http://localhost:8000}/api/v1"
TOKEN_FILE="$HOME/.vinyldigger/tokens.json"

# Ensure token directory exists
mkdir -p "$(dirname "$TOKEN_FILE")"

# Functions
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"

    local auth_header=""
    if [ -f "$TOKEN_FILE" ]; then
        local access_token=$(jq -r '.access_token // empty' "$TOKEN_FILE")
        if [ -n "$access_token" ]; then
            auth_header="Authorization: Bearer $access_token"
        fi
    fi

    if [ -n "$data" ]; then
        curl -s -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            ${auth_header:+-H "$auth_header"} \
            -d "$data"
    else
        curl -s -X "$method" "$BASE_URL$endpoint" \
            ${auth_header:+-H "$auth_header"}
    fi
}

login() {
    local email="$1"
    local password="$2"

    local response=$(curl -s -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$email&password=$password")

    echo "$response" > "$TOKEN_FILE"
    echo "Logged in successfully"
}

refresh_token() {
    if [ ! -f "$TOKEN_FILE" ]; then
        echo "Not logged in"
        return 1
    fi

    local refresh_token=$(jq -r '.refresh_token' "$TOKEN_FILE")
    local response=$(api_call POST "/auth/refresh" "{\"refresh_token\": \"$refresh_token\"}")

    echo "$response" > "$TOKEN_FILE"
    echo "Token refreshed"
}

create_search() {
    local name="$1"
    local artist="$2"
    local condition="$3"
    local max_price="$4"

    api_call POST "/searches" "{
        \"name\": \"$name\",
        \"search_type\": \"vinyl\",
        \"search_params\": {
            \"artist\": \"$artist\",
            \"min_condition\": \"$condition\",
            \"max_price\": $max_price
        },
        \"is_active\": true
    }"
}

# Main command handling
case "$1" in
    login)
        login "$2" "$3"
        ;;
    refresh)
        refresh_token
        ;;
    search)
        create_search "$2" "$3" "$4" "$5"
        ;;
    results)
        api_call GET "/searches/$2/results?limit=10" | jq
        ;;
    *)
        echo "Usage: $0 {login|refresh|search|results} [args...]"
        echo "  login <email> <password>"
        echo "  refresh"
        echo "  search <name> <artist> <condition> <max_price>"
        echo "  results <search_id>"
        exit 1
        ;;
esac
```

## Postman Collection

```json
{
  "info": {
    "name": "VinylDigger API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "bearer",
    "bearer": [
      {
        "key": "token",
        "value": "{{access_token}}",
        "type": "string"
      }
    ]
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000/api/v1"
    },
    {
      "key": "access_token",
      "value": ""
    },
    {
      "key": "refresh_token",
      "value": ""
    }
  ],
  "item": [
    {
      "name": "Authentication",
      "item": [
        {
          "name": "Register",
          "request": {
            "method": "POST",
            "header": [],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"email\": \"collector@example.com\",\n  \"password\": \"SecurePass123!\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": {
              "raw": "{{base_url}}/auth/register",
              "host": ["{{base_url}}"],
              "path": ["auth", "register"]
            }
          }
        },
        {
          "name": "Login",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "if (pm.response.code === 200) {",
                  "    const response = pm.response.json();",
                  "    pm.environment.set('access_token', response.access_token);",
                  "    pm.environment.set('refresh_token', response.refresh_token);",
                  "}"
                ],
                "type": "text/javascript"
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [],
            "body": {
              "mode": "urlencoded",
              "urlencoded": [
                {
                  "key": "username",
                  "value": "collector@example.com",
                  "type": "text"
                },
                {
                  "key": "password",
                  "value": "SecurePass123!",
                  "type": "text"
                }
              ]
            },
            "url": {
              "raw": "{{base_url}}/auth/login",
              "host": ["{{base_url}}"],
              "path": ["auth", "login"]
            }
          }
        },
        {
          "name": "Get Current User",
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "{{base_url}}/auth/me",
              "host": ["{{base_url}}"],
              "path": ["auth", "me"]
            }
          }
        }
      ]
    },
    {
      "name": "Searches",
      "item": [
        {
          "name": "Create Search",
          "request": {
            "method": "POST",
            "header": [],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"name\": \"Rare Jazz Vinyl\",\n  \"search_type\": \"vinyl\",\n  \"search_params\": {\n    \"artist\": \"John Coltrane\",\n    \"min_condition\": \"VG\",\n    \"max_price\": 150\n  },\n  \"is_active\": true\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": {
              "raw": "{{base_url}}/searches",
              "host": ["{{base_url}}"],
              "path": ["searches"]
            }
          }
        },
        {
          "name": "Get All Searches",
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "{{base_url}}/searches",
              "host": ["{{base_url}}"],
              "path": ["searches"]
            }
          }
        },
        {
          "name": "Get Search Results",
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "{{base_url}}/searches/:search_id/results?skip=0&limit=20",
              "host": ["{{base_url}}"],
              "path": ["searches", ":search_id", "results"],
              "query": [
                {
                  "key": "skip",
                  "value": "0"
                },
                {
                  "key": "limit",
                  "value": "20"
                }
              ],
              "variable": [
                {
                  "key": "search_id",
                  "value": "1"
                }
              ]
            }
          }
        }
      ]
    }
  ]
}
```

## Error Handling

All clients should handle these common error responses:

```json
// 400 Bad Request
{
  "detail": "Email already registered"
}

// 401 Unauthorized
{
  "detail": "Invalid authentication credentials"
}

// 422 Validation Error
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "invalid email address",
      "type": "value_error.email"
    }
  ]
}

// 500 Internal Server Error
{
  "detail": "Internal server error"
}
```

## Best Practices

1. **Token Management**
   - Store tokens securely (keychain, environment variables)
   - Refresh tokens proactively before expiry
   - Handle 401 responses by refreshing and retrying

2. **Rate Limiting**
   - Respect rate limits (future implementation)
   - Implement exponential backoff for retries
   - Cache responses when appropriate

3. **Error Handling**
   - Always check response status codes
   - Parse error messages for user feedback
   - Log errors for debugging

4. **Security**
   - Use HTTPS in production
   - Never log sensitive data
   - Validate SSL certificates

5. **Performance**
   - Use connection pooling
   - Implement request timeouts
   - Batch operations when possible
