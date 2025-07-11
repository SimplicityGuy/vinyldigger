import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'

// We'll import the token service fresh for each test
let tokenService: {
  setTokens: (access: string, refresh: string) => void
  getAccessToken: () => string | null
  getRefreshToken: () => string | null
  clearTokens: () => void
  hasValidTokens: () => boolean
  updateAccessToken: (token: string) => void
  loadTokens?: () => void
}

describe('tokenService', () => {
  // Create storage mocks with actual implementation
  const sessionStorageData: Record<string, string> = {}
  const localStorageData: Record<string, string> = {}

  beforeEach(async () => {
    // Clear storage data
    Object.keys(sessionStorageData).forEach(key => delete sessionStorageData[key])
    Object.keys(localStorageData).forEach(key => delete localStorageData[key])

    // Mock sessionStorage
    Object.defineProperty(window, 'sessionStorage', {
      value: {
        getItem: vi.fn((key: string) => sessionStorageData[key] || null),
        setItem: vi.fn((key: string, value: string) => {
          sessionStorageData[key] = value
        }),
        removeItem: vi.fn((key: string) => {
          delete sessionStorageData[key]
        }),
        clear: vi.fn(() => {
          Object.keys(sessionStorageData).forEach(key => delete sessionStorageData[key])
        }),
      },
      writable: true,
    })

    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn((key: string) => localStorageData[key] || null),
        setItem: vi.fn((key: string, value: string) => {
          localStorageData[key] = value
        }),
        removeItem: vi.fn((key: string) => {
          delete localStorageData[key]
        }),
        clear: vi.fn(() => {
          Object.keys(localStorageData).forEach(key => delete localStorageData[key])
        }),
      },
      writable: true,
    })

    vi.clearAllMocks()

    // Reset module cache to get a fresh instance
    vi.resetModules()
    const module = await import('@/lib/token-service')
    tokenService = module.tokenService
  })

  afterEach(() => {
    Object.keys(sessionStorageData).forEach(key => delete sessionStorageData[key])
    Object.keys(localStorageData).forEach(key => delete localStorageData[key])
  })

  describe('setTokens', () => {
    it('should store tokens correctly', () => {
      const accessToken = 'test-access-token'
      const refreshToken = 'test-refresh-token'

      tokenService.setTokens(accessToken, refreshToken)

      expect(sessionStorage.getItem('access_token')).toBe(accessToken)
      expect(tokenService.getAccessToken()).toBe(accessToken)

      const storedRefresh = localStorage.getItem('refresh_token')
      expect(storedRefresh).toBeTruthy()
      const parsed = JSON.parse(storedRefresh!)
      expect(parsed.token).toBe(refreshToken)
      expect(parsed.expiry).toBeGreaterThan(Date.now())
    })
  })

  describe('getAccessToken', () => {
    it('should return access token from memory', () => {
      tokenService.setTokens('access-123', 'refresh-123')
      expect(tokenService.getAccessToken()).toBe('access-123')
    })

    it('should return null when no token', () => {
      expect(tokenService.getAccessToken()).toBe(null)
    })
  })

  describe('getRefreshToken', () => {
    it('should return refresh token from memory', () => {
      tokenService.setTokens('access-123', 'refresh-123')
      expect(tokenService.getRefreshToken()).toBe('refresh-123')
    })

    it('should return null when no token', () => {
      expect(tokenService.getRefreshToken()).toBe(null)
    })

    it('should return null for expired refresh token', () => {
      // Set an expired refresh token
      const expiredData = {
        token: 'expired-refresh-token',
        expiry: Date.now() - 1000, // 1 second ago
      }
      localStorageData['refresh_token'] = JSON.stringify(expiredData)

      // Force reload tokens
      tokenService.loadTokens?.()

      expect(tokenService.getRefreshToken()).toBe(null)
      expect(localStorageData['refresh_token']).toBeUndefined()
    })
  })

  describe('clearTokens', () => {
    it('should clear all tokens', () => {
      tokenService.setTokens('access-123', 'refresh-123')

      tokenService.clearTokens()

      expect(sessionStorage.getItem('access_token')).toBe(null)
      expect(localStorage.getItem('refresh_token')).toBe(null)
      expect(tokenService.getAccessToken()).toBe(null)
      expect(tokenService.getRefreshToken()).toBe(null)
    })
  })

  describe('hasValidTokens', () => {
    it('should return true when both tokens exist', () => {
      tokenService.setTokens('access-123', 'refresh-123')
      expect(tokenService.hasValidTokens()).toBe(true)
    })

    it('should return false when no tokens', () => {
      expect(tokenService.hasValidTokens()).toBe(false)
    })

    it('should return false when only access token exists', () => {
      sessionStorage.setItem('access_token', 'access-123')
      tokenService.loadTokens?.()
      expect(tokenService.hasValidTokens()).toBe(false)
    })

    it('should return false when only refresh token exists', () => {
      const refreshData = {
        token: 'refresh-123',
        expiry: Date.now() + 100000,
      }
      localStorage.setItem('refresh_token', JSON.stringify(refreshData))
      tokenService.loadTokens?.()
      expect(tokenService.hasValidTokens()).toBe(false)
    })
  })

  describe('updateAccessToken', () => {
    it('should update only the access token', () => {
      tokenService.setTokens('old-access', 'refresh-123')

      tokenService.updateAccessToken('new-access')

      expect(tokenService.getAccessToken()).toBe('new-access')
      expect(tokenService.getRefreshToken()).toBe('refresh-123')
      expect(sessionStorage.getItem('access_token')).toBe('new-access')
    })
  })

  describe('loadTokens', () => {
    it('should load valid tokens from storage on initialization', () => {
      // Set tokens in storage directly in the mock data
      sessionStorageData['access_token'] = 'stored-access'
      const refreshData = {
        token: 'stored-refresh',
        expiry: Date.now() + 100000,
      }
      localStorageData['refresh_token'] = JSON.stringify(refreshData)

      // Force reload
      tokenService.loadTokens?.()

      expect(tokenService.getAccessToken()).toBe('stored-access')
      expect(tokenService.getRefreshToken()).toBe('stored-refresh')
    })

    it('should handle invalid JSON in refresh token', () => {
      localStorageData['refresh_token'] = 'invalid-json'

      // Force reload - should not throw
      tokenService.loadTokens?.()

      expect(tokenService.getRefreshToken()).toBe(null)
      expect(localStorageData['refresh_token']).toBeUndefined()
    })
  })
})
