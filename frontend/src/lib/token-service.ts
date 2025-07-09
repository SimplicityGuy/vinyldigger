interface TokenStorage {
  access_token: string | null
  refresh_token: string | null
}

class TokenService {
  private ACCESS_TOKEN_KEY = 'access_token'
  private REFRESH_TOKEN_KEY = 'refresh_token'

  // Use session storage for access token (more secure than localStorage)
  // and localStorage for refresh token with additional security measures
  private tokenStorage: TokenStorage = {
    access_token: null,
    refresh_token: null,
  }

  constructor() {
    // Initialize from storage on creation
    this.loadTokens()
  }

  private loadTokens() {
    // Access token from sessionStorage (cleared on tab close)
    this.tokenStorage.access_token = sessionStorage.getItem(this.ACCESS_TOKEN_KEY)

    // Refresh token from localStorage with expiry check
    const refreshData = localStorage.getItem(this.REFRESH_TOKEN_KEY)
    if (refreshData) {
      try {
        const { token, expiry } = JSON.parse(refreshData)
        if (new Date().getTime() < expiry) {
          this.tokenStorage.refresh_token = token
        } else {
          // Clean up expired token
          localStorage.removeItem(this.REFRESH_TOKEN_KEY)
        }
      } catch {
        // Invalid data, clean up
        localStorage.removeItem(this.REFRESH_TOKEN_KEY)
      }
    }
  }

  setTokens(accessToken: string, refreshToken: string) {
    // Store access token in sessionStorage (more secure)
    sessionStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken)
    this.tokenStorage.access_token = accessToken

    // Store refresh token with expiry (30 days)
    const refreshData = {
      token: refreshToken,
      expiry: new Date().getTime() + 30 * 24 * 60 * 60 * 1000
    }
    localStorage.setItem(this.REFRESH_TOKEN_KEY, JSON.stringify(refreshData))
    this.tokenStorage.refresh_token = refreshToken
  }

  getAccessToken(): string | null {
    return this.tokenStorage.access_token
  }

  getRefreshToken(): string | null {
    return this.tokenStorage.refresh_token
  }

  clearTokens() {
    sessionStorage.removeItem(this.ACCESS_TOKEN_KEY)
    localStorage.removeItem(this.REFRESH_TOKEN_KEY)
    this.tokenStorage = {
      access_token: null,
      refresh_token: null,
    }
  }

  // Check if we have valid tokens
  hasValidTokens(): boolean {
    this.loadTokens() // Refresh from storage
    return !!(this.tokenStorage.access_token && this.tokenStorage.refresh_token)
  }

  // Update only access token (used after refresh)
  updateAccessToken(accessToken: string) {
    sessionStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken)
    this.tokenStorage.access_token = accessToken
  }
}

// Export singleton instance
export const tokenService = new TokenService()

// Security recommendations for production:
// 1. Use httpOnly cookies instead of any client storage
// 2. Implement CSRF protection
// 3. Use secure flag for cookies in production
// 4. Add token rotation on each request
// 5. Implement proper token expiry handling
