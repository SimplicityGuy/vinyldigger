# OAuth Setup Guide

VinylDigger supports OAuth authentication for both Discogs and eBay, providing secure access to their APIs without storing your credentials.

## Overview

- **Discogs**: Uses OAuth 1.0a
- **eBay**: Uses OAuth 2.0
- **Security**: No passwords are stored - only secure OAuth tokens
- **User Experience**: Simple one-time authorization process

## Discogs OAuth Setup

### Prerequisites
1. A Discogs account
2. Access to VinylDigger Settings page

### Authorization Process
1. Navigate to **Settings** in VinylDigger
2. Under **Platform Authorizations**, find the **Discogs** section
3. Click **Connect Discogs Account**
4. You'll be redirected to Discogs to authorize VinylDigger
5. After authorization, copy the verification code shown on Discogs
6. Return to VinylDigger and enter the verification code
7. Click **Verify** to complete the connection

### Features Available
- Search Discogs marketplace
- Sync your collection
- Sync your want list
- Access your Discogs username

### Revoking Access
- Click **Revoke Access** in Settings to disconnect
- You can also revoke access from your Discogs account settings

## eBay OAuth Setup

### Prerequisites
1. An eBay account
2. Access to VinylDigger Settings page

### Authorization Process
1. Navigate to **Settings** in VinylDigger
2. Under **Platform Authorizations**, find the **eBay** section
3. Click **Connect eBay Account**
4. You'll be redirected to eBay to authorize VinylDigger
5. After authorization, you'll either:
   - Be automatically redirected back (if using standard flow)
   - Need to copy the authorization code and enter it manually
6. If manual entry is required, paste the code and click **Verify**

### Features Available
- Search eBay marketplace
- Access detailed item information
- View seller information
- Track pricing and availability

### Revoking Access
- Click **Revoke Access** in Settings to disconnect
- You can also manage app permissions in your eBay account settings

## Troubleshooting

### Common Issues

#### "Authorization Failed"
- Ensure you're logged into the correct account (Discogs/eBay)
- Check that you copied the entire verification/authorization code
- Try the authorization process again

#### "Token Expired"
- OAuth tokens may expire after extended periods
- Simply re-authorize by clicking the connect button again

#### Popup Blocked
- Ensure your browser allows popups from VinylDigger
- You can also open the authorization URL in a new tab manually

### Manual OAuth Flow
If the automatic redirect doesn't work:
1. The authorization window will show a code
2. Copy this code completely
3. Return to VinylDigger Settings
4. Paste the code in the verification field
5. Click Verify

## Security Notes

- VinylDigger never sees your Discogs or eBay passwords
- OAuth tokens are encrypted and stored securely
- Tokens are isolated per user - no sharing between accounts
- You can revoke access at any time from either VinylDigger or the platform

## Legacy API Key Support

While OAuth is recommended, VinylDigger still supports API keys for backward compatibility:
- API keys can be entered in the Settings page
- Keys are encrypted before storage
- OAuth takes precedence if both are configured

## Developer Information

For developers implementing or debugging OAuth:

### OAuth Endpoints
- **Initiate**: `POST /api/v1/oauth/authorize/{provider}`
- **Callback**: `GET /api/v1/oauth/callback/{provider}`
- **Verify**: `POST /api/v1/oauth/verify/{provider}`
- **Revoke**: `POST /api/v1/oauth/revoke/{provider}`
- **Status**: `GET /api/v1/oauth/status/{provider}`

### Local Development
For local development, the redirect URLs are:
- **Discogs**: `http://localhost:8000/api/v1/oauth/callback/discogs`
- **eBay**: `http://localhost:8000/api/v1/oauth/redirect/ebay`

### Environment Variables
OAuth functionality requires these to be set by the admin:
```env
# Discogs OAuth (set via admin panel)
DISCOGS_CONSUMER_KEY=your_consumer_key
DISCOGS_CONSUMER_SECRET=your_consumer_secret

# eBay OAuth (set via admin panel)
EBAY_CLIENT_ID=your_client_id
EBAY_CLIENT_SECRET=your_client_secret
```

### Recent Updates (July 2025)

#### eBay OAuth Environment Detection
VinylDigger now automatically detects eBay environment based on App ID:
- **Sandbox**: App IDs containing `SBX` automatically use sandbox endpoints
- **Production**: App IDs containing `PRD` automatically use production endpoints
- **Legacy**: Manual environment configuration still supported

#### Enhanced Error Handling
- Better error messages for OAuth failures
- Automatic token refresh attempts
- Improved debugging information in logs

#### Token Storage Improvements
- Increased token field lengths to 5000 characters
- Support for larger OAuth tokens from eBay
- Backward compatibility with existing tokens

For detailed technical information about recent OAuth fixes, see [OAuth Authentication Fixes](backend/oauth-authentication-fixes.md).

## Need Help?

If you encounter issues with OAuth setup:
1. Check the browser console for errors
2. Ensure popups are allowed
3. Try clearing cookies and reauthorizing
4. Contact support with specific error messages
