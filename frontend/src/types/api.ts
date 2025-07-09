export interface User {
  id: string
  email: string
  discogs_username?: string
  created_at: string
  updated_at: string
}

export interface ApiKey {
  id: string
  service: 'discogs' | 'ebay'
  username: string
  created_at: string
}

export interface UserPreferences {
  email_notifications: boolean
  search_frequency: string
  max_price: number
  min_condition: string
}

export interface Search {
  id: string
  name: string
  query: string
  platform: string
  platforms: string[]
  max_price?: number
  min_condition?: string
  is_active: boolean
  created_at: string
  updated_at: string
  last_run?: string
  last_checked_at?: string
  check_interval_hours: number
  result_count?: number
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RegisterData {
  email: string
  password: string
  discogs_username?: string
}

export interface LoginData {
  email: string
  password: string
}

export interface ApiKeyData {
  service: 'discogs' | 'ebay'
  key: string
  secret?: string
}

export interface SearchData {
  name: string
  query: string
  platforms: string[]
  max_price?: number
  min_condition?: string
}
