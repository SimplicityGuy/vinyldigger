# eBay Developer Setup Guide for VinylDigger

## Overview

This guide helps you set up eBay OAuth2 authentication for VinylDigger. eBay requires HTTPS redirect URLs and has deprecated the out-of-band (OOB) OAuth flow (`urn:ietf:wg:oauth:2.0:oob`) as of 2024.

## Prerequisites

- eBay Developer Account ([developer.ebay.com](https://developer.ebay.com/))
- VinylDigger running locally or deployed
- Admin access to VinylDigger

## The Challenge

eBay's "auth accepted URL" requires:
- ✅ HTTPS protocol (no HTTP allowed)
- ✅ Public domain (no localhost)
- ✅ Valid SSL certificate
- ❌ No support for `urn:ietf:wg:oauth:2.0:oob` (deprecated)

## Environment Support

VinylDigger now automatically detects whether to use eBay Production or Sandbox based on your App ID:
- **Sandbox**: App IDs containing `SBX` (e.g., `YourName-AppName-SBX-123456-abcdef`)
- **Production**: App IDs containing `PRD` (e.g., `YourName-AppName-PRD-123456-abcdef`)

This means you can use either environment without code changes!

## Solution Options

### Option 1: Static HTML Page (Recommended for Quick Setup)

This is the simplest solution that works immediately without any local tunneling.

#### Using Netlify Drop (Fastest - 2 minutes)

1. **Prepare the HTML file**
   - Copy `docs/ebay-oauth-redirect.html` and rename it to `index.html`

2. **Deploy to Netlify**
   - Go to [app.netlify.com/drop](https://app.netlify.com/drop)
   - Drag and drop your `index.html` file
   - Get instant HTTPS URL (e.g., `https://amazing-site-name.netlify.app/`)

3. **Configure eBay Developer App**
   - Log into [eBay Developer Program](https://developer.ebay.com/)
   - Go to your application settings
   - Set **Auth accepted URL** to your Netlify URL

4. **Update VinylDigger**
   - Go to VinylDigger admin settings
   - Update eBay OAuth **Redirect URI** to match your Netlify URL

#### Alternative Static Hosting Options

**GitHub Pages** (Permanent URL)
```bash
# Create repo, add index.html, enable GitHub Pages
# URL: https://yourusername.github.io/vinyldigger-oauth/
```

**Vercel** (CLI Deploy)
```bash
npm i -g vercel
vercel  # in directory with index.html
# URL: https://your-project.vercel.app/
```

**Surge.sh** (Simple CLI)
```bash
npm install -g surge
surge  # in directory with index.html
# Choose domain: vinyldigger-oauth.surge.sh
```

### Option 2: ngrok (Best for Active Development)

Use ngrok to create a secure HTTPS tunnel to your local VinylDigger instance.

#### Setup Steps

1. **Install ngrok**
   ```bash
   # macOS with Homebrew
   brew install ngrok/ngrok/ngrok

   # Or download from https://ngrok.com/download
   ```

2. **Start ngrok tunnel**
   ```bash
   ngrok http 8000
   ```

   You'll see:
   ```
   Forwarding: https://abc123.ngrok-free.app -> http://localhost:8000
   ```

3. **Configure eBay Developer App**
   - Set **Auth accepted URL** to: `https://abc123.ngrok-free.app/api/v1/oauth/redirect/ebay`

4. **Update VinylDigger**
   - Set **Redirect URI** to: `https://abc123.ngrok-free.app/api/v1/oauth/redirect/ebay`

**Note**: Free ngrok URLs change on restart. Consider paid ngrok for fixed subdomain.

### Option 3: Alternative Tunneling Services

**LocalTunnel** (Consistent subdomain)
```bash
npm install -g localtunnel
lt --port 8000 --subdomain vinyldigger
# URL: https://vinyldigger.loca.lt
```

**Cloudflare Tunnel** (If you own a domain)
- Set up Cloudflare Tunnel
- Point subdomain to localhost:8000
- Use: `https://oauth.yourdomain.com/api/v1/oauth/redirect/ebay`

### Option 4: Other Services

- **OAuth.io**: Specialized OAuth proxy service
- **Pipedream**: Create webhook workflows with public URLs
- **Make.com**: Webhook scenarios with OAuth handling

## How the OAuth Flow Works

1. **User initiates connection**
   - Clicks "Connect eBay" in VinylDigger
   - Gets redirected to eBay authorization page

2. **User authorizes on eBay**
   - Logs into eBay account
   - Approves VinylDigger access

3. **eBay redirects back**
   - To your configured redirect URL with `?code=XXX&state=YYY`

4. **Authorization code displayed**
   - Static page: Shows code and state for manual copying
   - Direct redirect: VinylDigger's handler shows the values

5. **User completes flow**
   - Copies authorization code and state
   - Pastes into VinylDigger verification form
   - VinylDigger exchanges code for access token

## Troubleshooting

### Common Issues

**"unauthorized_client" error**
- Redirect URI in VinylDigger doesn't match eBay Developer App exactly
- Using wrong environment credentials (sandbox vs production)
- Client ID/Secret mismatch

**"Invalid redirect_uri" error**
- eBay requires HTTPS (no HTTP)
- Must be exact match including trailing slashes
- Cannot use localhost or private IPs

**No authorization code displayed**
- Check browser console for JavaScript errors
- Ensure you're using the correct static HTML file
- Verify redirect URL includes query parameters

### Quick Fixes

1. **Double-check URLs match exactly** between eBay and VinylDigger
2. **Use production credentials** (not sandbox) for live eBay
3. **Clear browser cache** if seeing old redirect behavior
4. **Test with fresh ngrok URL** if tunneling issues

## Security Considerations

- State parameter prevents CSRF attacks
- Authorization codes are single-use and expire quickly
- No sensitive data stored in static redirect pages
- Manual copy/paste adds user verification step

## Recommended Approach

For most users, we recommend:

1. **Development**: Use ngrok for local testing
2. **Production**: Deploy proper HTTPS endpoint
3. **Quick testing**: Use static HTML with Netlify Drop

The static HTML solution is particularly good because:
- No maintenance required
- Works immediately
- Free forever
- No tunnels that can disconnect

## Sandbox vs Production Setup

### Using eBay Sandbox (for Testing)
1. Go to [eBay Developer Portal](https://developer.ebay.com/)
2. Click the **Sandbox** tab
3. Get your Sandbox App ID (contains `SBX`)
4. Use sandbox redirect URLs (same setup as production)
5. VinylDigger will automatically use sandbox endpoints

### Using eBay Production (for Live Data)
1. Go to [eBay Developer Portal](https://developer.ebay.com/)
2. Click the **Production** tab
3. Get your Production App ID (contains `PRD`)
4. Use production redirect URLs
5. VinylDigger will automatically use production endpoints

**Note**: You can easily switch between environments by updating your App ID and Cert ID in VinylDigger admin settings. No code changes needed!

## Next Steps

After successful OAuth setup:
1. Test the connection thoroughly
2. Set up your eBay search preferences
3. Configure notification settings
4. Start discovering vinyl deals!

## Need Help?

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Verify all URLs match exactly
3. Ensure you're using production (not sandbox) credentials
4. Review eBay Developer App settings
