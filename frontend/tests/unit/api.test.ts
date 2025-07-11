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
    ;(global.fetch as any).mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })


  describe('auth methods', () => {
    it('should login successfully', async () => {
      const mockTokens = { access_token: 'access', refresh_token: 'refresh', token_type: 'bearer' }
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens,
      })

      const result = await api.login('test@example.com', 'password')

      expect(tokenService.setTokens).toHaveBeenCalledWith('access', 'refresh')
      expect(result).toEqual(mockTokens)
    })

    it('should register successfully', async () => {
      const mockUser = { id: '123', email: 'test@example.com' }
      ;(global.fetch as any).mockResolvedValueOnce({
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
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSearches,
      })
      ;(tokenService.getAccessToken as any).mockReturnValue('test-token')

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
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCreated,
      })
      ;(tokenService.getAccessToken as any).mockReturnValue('test-token')

      const result = await api.createSearch(newSearch as any)

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
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Search started' }),
      })
      ;(tokenService.getAccessToken as any).mockReturnValue('test-token')

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
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })
      ;(tokenService.getAccessToken as any).mockReturnValue('test-token')

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
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPrefs,
      })
      ;(tokenService.getAccessToken as any).mockReturnValue('test-token')

      const result = await api.getPreferences()

      expect(result).toEqual(mockPrefs)
    })

    it('should update preferences', async () => {
      const updates = { discogs_username: 'newuser' }
      const mockUpdated = { ...updates, ebay_max_price: 100 }
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdated,
      })
      ;(tokenService.getAccessToken as any).mockReturnValue('test-token')

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
})