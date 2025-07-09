import { z } from 'zod'

const API_BASE_URL = '/api/v1'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('access_token')

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new ApiError(response.status, errorData.detail || 'Request failed')
  }

  return response
}

// Auth schemas
export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

export const registerSchema = loginSchema.extend({
  discogs_username: z.string().optional(),
})

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
      headers: {},
    })

    const result = await response.json()
    const tokens = tokenSchema.parse(result)

    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)

    return tokens
  },

  async register(data: z.infer<typeof registerSchema>) {
    const response = await fetchApi('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })

    return response.json()
  },

  async getMe() {
    const response = await fetchApi('/auth/me')
    return response.json()
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}

export const configApi = {
  async updateApiKey(service: string, key: string, secret?: string) {
    const response = await fetchApi('/config/api-keys', {
      method: 'PUT',
      body: JSON.stringify({ service, key, secret }),
    })
    return response.json()
  },

  async getApiKeys() {
    const response = await fetchApi('/config/api-keys')
    return response.json()
  },

  async getPreferences() {
    const response = await fetchApi('/config/preferences')
    return response.json()
  },

  async updatePreferences(data: Record<string, unknown>) {
    const response = await fetchApi('/config/preferences', {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return response.json()
  },
}

export const searchApi = {
  async createSearch(data: Record<string, unknown>) {
    const response = await fetchApi('/searches', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async getSearches() {
    const response = await fetchApi('/searches')
    return response.json()
  },

  async runSearch(searchId: string) {
    const response = await fetchApi(`/searches/${searchId}/run`, {
      method: 'POST',
    })
    return response.json()
  },

  async getSearchResults(searchId: string) {
    const response = await fetchApi(`/searches/${searchId}/results`)
    return response.json()
  },

  async deleteSearch(searchId: string) {
    const response = await fetchApi(`/searches/${searchId}`, {
      method: 'DELETE',
    })
    return response.json()
  },
}

export const collectionApi = {
  async syncCollection() {
    const response = await fetchApi('/collections/sync', {
      method: 'POST',
    })
    return response.json()
  },

  async getCollectionStatus() {
    const response = await fetchApi('/collections/status')
    return response.json()
  },

  async getWantListStatus() {
    const response = await fetchApi('/collections/wantlist/status')
    return response.json()
  },
}
