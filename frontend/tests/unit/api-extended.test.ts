import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as api from '../../src/lib/api';
import * as tokenService from '../../src/lib/token-service';

// Mock fetch globally
const mockFetch = vi.fn() as unknown as typeof fetch;
global.fetch = mockFetch;

// Mock fetch response type
const createMockResponse = <T>(data: T, ok = true, status = 200) => ({
  ok,
  status,
  statusText: ok ? 'OK' : 'Error',
  json: async () => data,
} as Response);

// Mock token service
vi.mock('../../src/lib/token-service', () => ({
  getAccessToken: vi.fn(),
  getRefreshToken: vi.fn(),
  setTokens: vi.fn(),
  removeTokens: vi.fn(),
}));

const mockedTokenService = tokenService as vi.Mocked<typeof tokenService>;

describe('Extended API Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedTokenService.getAccessToken.mockReturnValue('test-token');
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('Search Analysis Endpoints', () => {
    it('gets search analysis successfully', async () => {
      const mockAnalysis = {
        search_id: '123',
        total_results: 10,
        unique_items: 8,
        average_price: 25.99,
      };

      mockFetch.mockResolvedValueOnce(createMockResponse(mockAnalysis));

      const result = await api.getSearchAnalysis('123');

      expect(result).toEqual(mockAnalysis);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/analysis/search/123/analysis'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      );
    });

    it('gets multi-item deals successfully', async () => {
      const mockDeals = [
        {
          seller_name: 'VinylStore',
          item_count: 3,
          total_price: 75.0,
          items: [],
        },
      ];

      mockFetch.mockResolvedValueOnce(createMockResponse(mockDeals));

      const result = await api.getMultiItemDeals('123');

      expect(result).toEqual(mockDeals);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/analysis/search/123/multi-item-deals'),
        expect.any(Object)
      );
    });

    it('gets price comparison successfully', async () => {
      const mockComparison = {
        items: [
          {
            title: 'Test Album',
            artist: 'Test Artist',
            listings: [],
          },
        ],
      };

      mockFetch.mockResolvedValueOnce(createMockResponse(mockComparison));

      const result = await api.getPriceComparison('123');

      expect(result).toEqual(mockComparison);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/analysis/search/123/price-comparison'),
        expect.any(Object)
      );
    });
  });

  describe('OAuth Endpoints', () => {
    it('initiates Discogs OAuth successfully', async () => {
      const mockResponse = {
        auth_url: 'https://discogs.com/oauth/authorize?token=xyz',
      };

      mockFetch.mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await api.initiateDiscogsOAuth();

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/oauth/discogs/initiate'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('completes Discogs OAuth successfully', async () => {
      const mockResponse = {
        message: 'OAuth completed successfully',
      };

      mockFetch.mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await api.completeDiscogsOAuth('verifier123', 'token123');

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/oauth/discogs/callback'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            oauth_verifier: 'verifier123',
            oauth_token: 'token123',
          }),
        })
      );
    });

    it('initiates eBay OAuth successfully', async () => {
      const mockResponse = {
        auth_url: 'https://auth.ebay.com/oauth2/authorize?client_id=xyz',
      };

      mockFetch.mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await api.initiateEbayOAuth();

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/oauth/ebay/initiate'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('completes eBay OAuth successfully', async () => {
      const mockResponse = {
        message: 'OAuth completed successfully',
      };

      mockFetch.mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await api.completeEbayOAuth('auth_code_123');

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/oauth/ebay/callback'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ code: 'auth_code_123' }),
        })
      );
    });
  });

  describe('Collection Sync Endpoints', () => {
    it('syncs collection only successfully', async () => {
      const mockResponse = { message: 'Collection sync started' };

      mockFetch.mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await api.syncCollectionOnly();

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/collections/sync/collection'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('syncs wantlist only successfully', async () => {
      const mockResponse = { message: 'Wantlist sync started' };

      mockFetch.mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await api.syncWantlistOnly();

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/collections/sync/wantlist'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('User Profile Endpoints', () => {
    it('updates user profile successfully', async () => {
      const updateData = { email: 'newemail@example.com' };
      const mockResponse = {
        id: '123',
        email: 'newemail@example.com',
        created_at: '2025-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await api.updateUser(updateData);

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/auth/me'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(updateData),
        })
      );
    });
  });

  describe('Error Handling', () => {
    it('handles 401 unauthorized errors', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({}, false, 401));

      mockedTokenService.removeTokens.mockImplementation(() => {});

      await expect(api.getSearchAnalysis('123')).rejects.toThrow('Unauthorized');
      expect(mockedTokenService.removeTokens).toHaveBeenCalled();
    });

    it('handles network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(api.getSearchAnalysis('123')).rejects.toThrow('Network error');
    });

    it('handles JSON parsing errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => {
          throw new Error('Invalid JSON');
        },
      } as Response);

      await expect(api.getSearchAnalysis('123')).rejects.toThrow('Invalid JSON');
    });
  });

  describe('Refresh Token Handling', () => {
    it('refreshes token and retries on 401', async () => {
      const mockNewTokens = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'bearer',
      };

      // First call returns 401
      mockFetch.mockResolvedValueOnce(createMockResponse({}, false, 401));

      // Token refresh succeeds
      mockedTokenService.getRefreshToken.mockReturnValue('refresh-token');
      mockFetch.mockResolvedValueOnce(createMockResponse(mockNewTokens));

      // Retry succeeds
      const mockData = { test: 'data' };
      mockFetch.mockResolvedValueOnce(createMockResponse(mockData));

      const result = await api.getSearches();

      expect(result).toEqual(mockData);
      expect(mockedTokenService.setTokens).toHaveBeenCalledWith(
        mockNewTokens.access_token,
        mockNewTokens.refresh_token
      );
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it('handles refresh token failure', async () => {
      // First call returns 401
      mockFetch.mockResolvedValueOnce(createMockResponse({}, false, 401));

      // Token refresh fails
      mockedTokenService.getRefreshToken.mockReturnValue('refresh-token');
      mockFetch.mockResolvedValueOnce(createMockResponse({}, false, 400));

      await expect(api.getSearches()).rejects.toThrow('Bad Request');
      expect(mockedTokenService.removeTokens).toHaveBeenCalled();
    });
  });
});
