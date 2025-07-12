# Discogs OAuth Authentication Guide

VinylDigger uses Discogs OAuth 1.0a to securely access your Discogs account. This guide explains how the authentication process works.

## Overview

Unlike the old system where each user had to manage their own API keys, VinylDigger now uses a proper OAuth flow:

1. **Application Registration**: The VinylDigger administrator registers the application with Discogs once
2. **User Authorization**: Each user authorizes VinylDigger to access their Discogs account
3. **Secure Access**: VinylDigger can then search Discogs and sync your collection on your behalf

## For Users

### Connecting Your Discogs Account

1. Go to **Settings** in VinylDigger
2. In the **Platform Authorizations** section, find Discogs
3. Click **Connect Discogs Account**
4. You'll be redirected to Discogs to authorize VinylDigger
5. Log in to your Discogs account if needed
6. Click **Authorize** to grant VinylDigger access
7. You'll be redirected back to VinylDigger
8. Your Discogs account is now connected!

### What VinylDigger Can Access

When you authorize VinylDigger, it can:
- Search the Discogs marketplace on your behalf
- Access your collection
- Access your wantlist
- View your username and basic profile info

VinylDigger cannot:
- Make purchases
- Modify your collection or wantlist
- Change your account settings
- Access your private messages

### Revoking Access

You can revoke VinylDigger's access at any time:

**From VinylDigger:**
1. Go to Settings
2. Click **Revoke Access** next to your connected Discogs account

**From Discogs:**
1. Go to your Discogs account settings
2. Navigate to Applications
3. Find VinylDigger and revoke its access

## For Administrators

### Initial Setup

Before users can connect their Discogs accounts, an administrator must configure the OAuth credentials:

1. **Register Your Application on Discogs**
   - Log in to Discogs
   - Go to [Settings > Developers](https://www.discogs.com/settings/developers)
   - Click "Create New Application"
   - Fill in:
     - Application Name: "VinylDigger" (or your instance name)
     - Homepage URL: Your VinylDigger URL
     - Description: Brief description of your instance
   - Save and note your Consumer Key and Consumer Secret

2. **Configure VinylDigger**
   - Log in to VinylDigger with an admin account
   - Go to **/admin** (you must be an admin user)
   - Click "Add OAuth Provider" or edit existing Discogs configuration
   - Enter:
     - Provider: Discogs
     - Consumer Key: From Discogs application
     - Consumer Secret: From Discogs application
     - Callback URL: `https://yourdomain.com/oauth/callback/discogs` (or leave empty for out-of-band)
   - Save the configuration

### Admin Requirements

Currently, admin users are identified by email domain. Users with emails ending in:
- `@admin.com`
- `@vinyldigger.com`

Are considered administrators and can access the admin panel.

### Security Considerations

- Consumer secrets are stored encrypted in the database
- Never expose consumer secrets in logs or client-side code
- Use HTTPS in production for secure OAuth flow
- Regularly audit which users have authorized access

## Troubleshooting

### "Discogs OAuth is not configured"
This means the administrator hasn't set up the Discogs OAuth credentials yet. Contact your VinylDigger administrator.

### "Authorization failed"
- Ensure you're logged in to the correct Discogs account
- Try clearing your browser cookies and cache
- Attempt the authorization again

### "User has not authorized Discogs access"
You need to connect your Discogs account in Settings before you can use Discogs features.

## Technical Details

VinylDigger implements the full OAuth 1.0a flow:

1. **Request Token**: VinylDigger gets a temporary request token from Discogs
2. **Authorization**: User is redirected to Discogs to authorize the request token
3. **Access Token**: VinylDigger exchanges the authorized request token for permanent access tokens
4. **API Access**: VinylDigger uses the access tokens to make API calls on your behalf

Access tokens are stored encrypted and associated with your user account. They remain valid until you revoke access.
