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
  SearchBudget,
  SearchBudgetSummary,
  SearchBudgetCreate,
  SearchBudgetUpdate,
  SearchTemplate,
  SearchTemplateCreate,
  SearchTemplateUpdate,
  SearchTemplateUse,
  SearchTemplatePreview,
  SearchChain,
  SearchChainCreate,
  SearchChainUpdate,
  SearchChainLink,
  SearchChainLinkCreate,
  SearchChainLinkUpdate,
  SearchOrchestrationUpdate,
  SearchScheduleSuggestion,
  BudgetAlert,
  SpendingAnalytics,
  TemplateAnalytics,
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

  async updateUser(data: { email: string }): Promise<User> {
    const response = await fetchApi('/auth/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    })
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

  async getSearch(searchId: string): Promise<SavedSearch> {
    const response = await fetchApi(`/searches/${searchId}`)
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

  async updateSearch(searchId: string, data: Partial<CreateSearchData>): Promise<SavedSearch> {
    const response = await fetchApi(`/searches/${searchId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return response.json()
  },
  async deleteSearch(searchId: string): Promise<{ message: string }> {
    const response = await fetchApi(`/searches/${searchId}`, {
      method: 'DELETE',
    })
    return response.json()
  },

  // Search Orchestration endpoints
  async updateSearchOrchestration(searchId: string, data: SearchOrchestrationUpdate): Promise<SavedSearch> {
    const response = await fetchApi(`/searches/${searchId}/orchestration`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async getScheduleSuggestion(searchId: string): Promise<SearchScheduleSuggestion> {
    const response = await fetchApi(`/searches/${searchId}/schedule-suggestion`)
    return response.json()
  },

  async getSearchDependencies(searchId: string): Promise<SavedSearch[]> {
    const response = await fetchApi(`/searches/${searchId}/dependencies`)
    return response.json()
  },

  async triggerSearchManually(searchId: string): Promise<{ message: string; search_id: string }> {
    const response = await fetchApi(`/searches/${searchId}/trigger`, {
      method: 'POST',
    })
    return response.json()
  },
}

export const searchAnalysisApi = {
  async getSearchAnalysis(searchId: string) {
    const response = await fetchApi(`/analysis/search/${searchId}/analysis`)
    return response.json()
  },

  async getMultiItemDeals(searchId: string) {
    const response = await fetchApi(`/analysis/search/${searchId}/multi-item-deals`)
    return response.json()
  },

  async getPriceComparison(searchId: string) {
    const response = await fetchApi(`/analysis/search/${searchId}/price-comparison`)
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

// Budget Management API
export const budgetApi = {
  async getCurrentBudget(): Promise<SearchBudget | null> {
    const response = await fetchApi('/budgets')
    return response.json()
  },

  async createBudget(data: SearchBudgetCreate): Promise<SearchBudget> {
    const response = await fetchApi('/budgets', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async updateBudget(budgetId: string, data: SearchBudgetUpdate): Promise<SearchBudget> {
    const response = await fetchApi(`/budgets/${budgetId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async getBudgetSummary(): Promise<SearchBudgetSummary> {
    const response = await fetchApi('/budgets/summary')
    return response.json()
  },

  async getBudgetUsage(): Promise<SearchBudgetSummary> {
    const response = await fetchApi('/budgets/summary')
    return response.json()
  },

  async getSpendingAnalytics(days = 30): Promise<SpendingAnalytics> {
    const response = await fetchApi(`/budgets/analytics?days=${days}`)
    return response.json()
  },

  async getBudgetAlerts(): Promise<BudgetAlert[]> {
    const response = await fetchApi('/budgets/alerts')
    return response.json()
  },

  async resetMonthlyBudget(): Promise<SearchBudget> {
    const response = await fetchApi('/budgets/reset', {
      method: 'POST',
    })
    return response.json()
  },
}

// Template Management API
export const templateApi = {
  async getTemplates(params?: {
    category?: string
    search?: string
    popular?: boolean
    limit?: number
  }): Promise<SearchTemplate[]> {
    const queryParams = new URLSearchParams()
    if (params?.category) queryParams.set('category', params.category)
    if (params?.search) queryParams.set('search', params.search)
    if (params?.popular) queryParams.set('popular', 'true')
    if (params?.limit) queryParams.set('limit', params.limit.toString())

    const response = await fetchApi(`/templates?${queryParams.toString()}`)
    return response.json()
  },

  async getTemplateCategories(): Promise<string[]> {
    const response = await fetchApi('/templates/categories')
    return response.json()
  },

  async getTemplateAnalytics(): Promise<TemplateAnalytics> {
    const response = await fetchApi('/templates/analytics/overview')
    return response.json()
  },

  async getTemplate(templateId: string): Promise<SearchTemplate> {
    const response = await fetchApi(`/templates/${templateId}`)
    return response.json()
  },

  async createTemplate(data: SearchTemplateCreate): Promise<SearchTemplate> {
    const response = await fetchApi('/templates', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async updateTemplate(templateId: string, data: SearchTemplateUpdate): Promise<SearchTemplate> {
    const response = await fetchApi(`/templates/${templateId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async deleteTemplate(templateId: string): Promise<void> {
    await fetchApi(`/templates/${templateId}`, {
      method: 'DELETE',
    })
  },

  async previewTemplate(templateId: string, parameters: Record<string, unknown>): Promise<SearchTemplatePreview> {
    const response = await fetchApi(`/templates/${templateId}/preview`, {
      method: 'POST',
      body: JSON.stringify(parameters),
    })
    return response.json()
  },

  async useTemplate(templateId: string, data: SearchTemplateUse): Promise<{ search_id: string; message: string }> {
    const response = await fetchApi(`/templates/${templateId}/use`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async validateTemplateParameters(templateId: string, parameters: Record<string, unknown>): Promise<{
    valid: boolean
    issues: string[]
    template_name: string
  }> {
    const response = await fetchApi(`/templates/${templateId}/validate`, {
      method: 'POST',
      body: JSON.stringify(parameters),
    })
    return response.json()
  },
}

// Search Chain Management API
export const chainApi = {
  async getChains(): Promise<SearchChain[]> {
    const response = await fetchApi('/chains')
    return response.json()
  },

  async getChain(chainId: string): Promise<SearchChain> {
    const response = await fetchApi(`/chains/${chainId}`)
    return response.json()
  },

  async createChain(data: SearchChainCreate): Promise<SearchChain> {
    const response = await fetchApi('/chains', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async updateChain(chainId: string, data: SearchChainUpdate): Promise<SearchChain> {
    const response = await fetchApi(`/chains/${chainId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async deleteChain(chainId: string): Promise<void> {
    await fetchApi(`/chains/${chainId}`, {
      method: 'DELETE',
    })
  },

  async getChainLinks(chainId: string): Promise<SearchChainLink[]> {
    const response = await fetchApi(`/chains/${chainId}/links`)
    return response.json()
  },

  async createChainLink(chainId: string, data: SearchChainLinkCreate): Promise<SearchChainLink> {
    const response = await fetchApi(`/chains/${chainId}/links`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async updateChainLink(chainId: string, linkId: string, data: SearchChainLinkUpdate): Promise<SearchChainLink> {
    const response = await fetchApi(`/chains/${chainId}/links/${linkId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async deleteChainLink(chainId: string, linkId: string): Promise<void> {
    await fetchApi(`/chains/${chainId}/links/${linkId}`, {
      method: 'DELETE',
    })
  },

  async evaluateChain(chainId: string): Promise<{
    chain_id: string
    chain_name: string
    triggered_searches: string[]
    count: number
    message: string
  }> {
    const response = await fetchApi(`/chains/${chainId}/evaluate`, {
      method: 'POST',
    })
    return response.json()
  },
}

// Default export for convenience
const api = {
  ...authApi,
  ...configApi,
  ...searchApi,
  ...searchAnalysisApi,
  ...collectionApi,
  ...oauthApi,
  ...budgetApi,
  ...templateApi,
  ...chainApi,
}

export default api
