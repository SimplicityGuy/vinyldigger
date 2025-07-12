import { z } from 'zod'
import { tokenService } from './token-service'
import type {
  User,
  SavedSearch,
  SearchResult,
  UserPreferences,
  CollectionStatus,
  CreateSearchData,
  UpdatePreferencesData,
} from '@/types/api'

const API_BASE_URL = '/api/v1'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const token = tokenService.getAccessToken()

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }

  // Only set Content-Type if not already set and body is not FormData
  if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: 'same-origin', // Include cookies for CSRF protection
  })

  // Handle token refresh on 401
  if (response.status === 401 && tokenService.getRefreshToken()) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      // Retry original request with new token
      const newToken = tokenService.getAccessToken()
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`
        return fetch(`${API_BASE_URL}${endpoint}`, {
          ...options,
          headers,
          credentials: 'same-origin',
        })
      }
    }
  }

  if (!response.ok) {
    let errorMessage = 'Request failed'
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorData.message || errorMessage
    } catch {
      // Response might not be JSON
      errorMessage = `HTTP ${response.status}: ${response.statusText}`
    }
    throw new ApiError(response.status, errorMessage)
  }

  return response
}

async function refreshAccessToken(): Promise<boolean> {
  try {
    const refreshToken = tokenService.getRefreshToken()
    if (!refreshToken) return false

    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
      credentials: 'same-origin',
    })

    if (response.ok) {
      const data = await response.json()
      const tokens = tokenSchema.parse(data)
      tokenService.updateAccessToken(tokens.access_token)
      return true
    }

    // Refresh failed, clear tokens
    tokenService.clearTokens()
    return false
  } catch {
    tokenService.clearTokens()
    return false
  }
}

// Auth schemas
export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

export const registerSchema = loginSchema

export const tokenSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
})

// API functions
export const authApi = {
  async login(data: z.infer<typeof loginSchema>) {
    const formData = new FormData()
    formData.append('username', data.email)
    formData.append('password', data.password)

    const response = await fetchApi('/auth/login', {
      method: 'POST',
      body: formData,
    })

    const result = await response.json()
    const tokens = tokenSchema.parse(result)

    tokenService.setTokens(tokens.access_token, tokens.refresh_token)

    return tokens
  },

  async register(data: z.infer<typeof registerSchema>) {
    const response = await fetchApi('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })

    return response.json()
  },

  async getMe(): Promise<User> {
    const response = await fetchApi('/auth/me')
    return response.json()
  },

  logout() {
    tokenService.clearTokens()
  },

  hasValidTokens() {
    return tokenService.hasValidTokens()
  },
}

export const configApi = {
  async getPreferences(): Promise<UserPreferences> {
    const response = await fetchApi('/config/preferences')
    return response.json()
  },

  async updatePreferences(data: UpdatePreferencesData): Promise<UserPreferences> {
    const response = await fetchApi('/config/preferences', {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return response.json()
  },
}

export const searchApi = {
  async createSearch(data: CreateSearchData): Promise<SavedSearch> {
    const response = await fetchApi('/searches', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async getSearches(): Promise<SavedSearch[]> {
    const response = await fetchApi('/searches')
    return response.json()
  },

  async runSearch(searchId: string): Promise<{ message: string }> {
    const response = await fetchApi(`/searches/${searchId}/run`, {
      method: 'POST',
    })
    return response.json()
  },

  async getSearchResults(searchId: string): Promise<SearchResult[]> {
    const response = await fetchApi(`/searches/${searchId}/results`)
    return response.json()
  },

  async deleteSearch(searchId: string): Promise<{ message: string }> {
    const response = await fetchApi(`/searches/${searchId}`, {
      method: 'DELETE',
    })
    return response.json()
  },
}

export const collectionApi = {
  async syncCollection(): Promise<{ message: string }> {
    const response = await fetchApi('/collections/sync', {
      method: 'POST',
    })
    return response.json()
  },

  async syncCollectionOnly(): Promise<{ message: string }> {
    const response = await fetchApi('/collections/sync/collection', {
      method: 'POST',
    })
    return response.json()
  },

  async syncWantListOnly(): Promise<{ message: string }> {
    const response = await fetchApi('/collections/sync/wantlist', {
      method: 'POST',
    })
    return response.json()
  },

  async getCollectionStatus(): Promise<CollectionStatus> {
    const response = await fetchApi('/collections/status')
    return response.json()
  },

  async getWantListStatus(): Promise<CollectionStatus> {
    const response = await fetchApi('/collections/wantlist/status')
    return response.json()
  },
}

export const oauthApi = {
  async getOAuthStatus(provider: string) {
    const response = await fetchApi(`/oauth/status/${provider}`)
    return response.json()
  },

  async initiateOAuth(provider: string) {
    const response = await fetchApi(`/oauth/authorize/${provider}`, {
      method: 'POST',
    })
    return response.json()
  },

  async discogsCallback(params: { oauth_token: string; oauth_verifier: string; state: string }) {
    const queryParams = new URLSearchParams(params).toString()
    const response = await fetchApi(`/oauth/callback/discogs?${queryParams}`)
    return response.json()
  },

  async revokeOAuth(provider: string) {
    const response = await fetchApi(`/oauth/revoke/${provider}`, {
      method: 'DELETE',
    })
    return response.json()
  },

  async verifyDiscogs(state: string, verificationCode: string) {
    const response = await fetchApi('/oauth/verify/discogs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        state,
        verification_code: verificationCode,
      }),
    })
    return response.json()
  },

  async ebayCallback(params: { code: string; state: string }) {
    const queryParams = new URLSearchParams(params).toString()
    const response = await fetchApi(`/oauth/callback/ebay?${queryParams}`)
    return response.json()
  },

  async verifyEbay(state: string, authorizationCode: string) {
    const response = await fetchApi('/oauth/verify/ebay', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        state,
        authorization_code: authorizationCode,
      }),
    })
    return response.json()
  },
}

// Default export for convenience
const api = {
  ...authApi,
  ...configApi,
  ...searchApi,
  ...collectionApi,
  ...oauthApi,
}

export default api
