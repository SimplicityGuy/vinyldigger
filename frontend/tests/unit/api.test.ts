import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { tokenService } from '@/lib/token-service'

// Mock fetch globally
global.fetch = vi.fn()

// Mock tokenService
vi.mock('@/lib/token-service', () => ({
  tokenService: {
    getAccessToken: vi.fn(),
    getRefreshToken: vi.fn(),
    setTokens: vi.fn(),
    updateAccessToken: vi.fn(),
    clearTokens: vi.fn(),
  },
}))

// Import api after mocks are set up
import api from '@/lib/api'

describe('api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset fetch mock
    vi.mocked(global.fetch).mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })


  describe('auth methods', () => {
    it('should login successfully', async () => {
      const mockTokens = { access_token: 'access', refresh_token: 'refresh', token_type: 'bearer' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens,
      })

      const result = await api.login('test@example.com', 'password')

      expect(tokenService.setTokens).toHaveBeenCalledWith('access', 'refresh')
      expect(result).toEqual(mockTokens)
    })

    it('should register successfully', async () => {
      const mockUser = { id: '123', email: 'test@example.com' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      })

      const result = await api.register('test@example.com', 'password')

      expect(result).toEqual(mockUser)
    })

    it('should logout and clear tokens', async () => {
      api.logout()
      expect(tokenService.clearTokens).toHaveBeenCalled()
    })
  })

  describe('searches methods', () => {
    it('should fetch searches', async () => {
      const mockSearches = [{ id: '1', name: 'Test Search' }]
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSearches,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.getSearches()

      expect(result).toEqual(mockSearches)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/searches'),
        expect.any(Object)
      )
    })

    it('should create search', async () => {
      const newSearch = { name: 'New Search', query: 'test' }
      const mockCreated = { id: '123', ...newSearch }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCreated,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.createSearch(newSearch as Parameters<typeof api.createSearch>[0])

      expect(result).toEqual(mockCreated)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/searches'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newSearch),
        })
      )
    })

    it('should run search', async () => {
      const searchId = '123'
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Search started' }),
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.runSearch(searchId)

      expect(result).toEqual({ message: 'Search started' })
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/v1/searches/${searchId}/run`),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })
  })

  describe('collections methods', () => {
    it('should sync collections', async () => {
      const mockResponse = { message: 'Sync started' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.syncCollection()

      expect(result).toEqual(mockResponse)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/collections/sync'),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })
  })

  describe('config methods', () => {
    it('should get preferences', async () => {
      const mockPrefs = { discogs_username: 'user123' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPrefs,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.getPreferences()

      expect(result).toEqual(mockPrefs)
    })

    it('should update preferences', async () => {
      const updates = { discogs_username: 'newuser' }
      const mockUpdated = { ...updates, ebay_max_price: 100 }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdated,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.updatePreferences(updates)

      expect(result).toEqual(mockUpdated)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/config/preferences'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(updates),
        })
      )
    })
  })

  describe('oauth methods', () => {
    it('should get OAuth status', async () => {
      const mockStatus = { is_authorized: true, username: 'testuser' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.getOAuthStatus('discogs')

      expect(result).toEqual(mockStatus)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/oauth/status/discogs'),
        expect.any(Object)
      )
    })

    it('should initiate OAuth', async () => {
      const mockResponse = { authorization_url: 'https://auth.ebay.com/...', state: 'abc123' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.initiateOAuth('ebay')

      expect(result).toEqual(mockResponse)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/oauth/authorize/ebay'),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })

    it('should handle eBay callback', async () => {
      const mockResponse = { message: 'Success', username: 'ebayuser' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.ebayCallback({ code: 'auth_code', state: 'state123' })

      expect(result).toEqual(mockResponse)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/oauth/callback/ebay?code=auth_code&state=state123'),
        expect.any(Object)
      )
    })

    it('should verify eBay authorization code', async () => {
      const mockResponse = { message: 'Success', username: 'ebayuser' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.verifyEbay('state123', 'auth_code_123')

      expect(result).toEqual(mockResponse)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/oauth/verify/ebay'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            state: 'state123',
            authorization_code: 'auth_code_123',
          }),
        })
      )
    })

    it('should revoke OAuth access', async () => {
      const mockResponse = { message: 'Successfully revoked EBAY access.' }
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })
      vi.mocked(tokenService.getAccessToken).mockReturnValue('test-token')

      const result = await api.revokeOAuth('ebay')

      expect(result).toEqual(mockResponse)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/oauth/revoke/ebay'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })
})
