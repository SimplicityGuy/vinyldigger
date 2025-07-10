# Discogs API Authentication

## Authentication Methods

VinylDigger supports two types of Discogs authentication:

### 1. Personal Access Token (Recommended)
- Generate a token at: https://www.discogs.com/settings/developers
- Tokens are longer (40+ characters) and may contain hyphens
- Uses `Authorization: Discogs token=YOUR_TOKEN` header
- Better rate limits and more reliable

### 2. OAuth Token
- Shorter tokens (typically 20-30 characters)
- Uses `?token=YOUR_TOKEN` query parameter
- Legacy authentication method

## Setup Instructions

1. Go to https://www.discogs.com/settings/developers
2. Click "Generate new token" under Personal Access Tokens
3. Copy the generated token
4. In VinylDigger, go to Settings > API Keys
5. Paste your token in the Discogs API Key field

## Important Notes

- The User-Agent header must include a contact URL as per Discogs requirements
- We use the v2 API with JSON response format
- Rate limiting is automatically handled with delays between requests
- Authentication errors will show as "401 Unauthorized" in logs

## Troubleshooting

If you're getting 401 errors:
1. Verify your token is correct (no extra spaces)
2. Check if the token hasn't expired
3. Ensure you're using a Personal Access Token for better reliability
4. Try generating a new token if issues persist
