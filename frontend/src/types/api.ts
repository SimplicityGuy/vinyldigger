// API type definitions

export interface User {
  id: string
  email: string
  created_at: string
  updated_at: string
}

export interface ApiKey {
  service: 'discogs' | 'ebay'
  has_key: boolean
  created_at?: string
  updated_at?: string
}

export interface SearchFilters {
  format?: string
  genre?: string
  style?: string
  year_from?: number
  year_to?: number
  min_price?: number
  max_price?: number
  condition?: string[]
  category_id?: string
  item_location?: string
  sort?: 'price_asc' | 'price_desc' | 'date_desc' | 'distance'
  limit?: number
  offset?: number
}

export interface SavedSearch {
  id: string
  name: string
  query: string
  platform: 'ebay' | 'discogs' | 'both'
  filters: SearchFilters
  is_active: boolean
  check_interval_hours: number
  last_run_at?: string
  created_at: string
  updated_at: string
  min_record_condition?: string
  min_sleeve_condition?: string
  seller_location_preference?: string
}

export interface SearchResult {
  id: string
  search_id: string
  platform: 'ebay' | 'discogs'
  item_id: string
  item_data: Record<string, unknown>
  is_in_collection: boolean
  is_in_wantlist: boolean
  created_at: string
}

export interface UserPreferences {
  email_notifications: boolean
  notification_frequency: 'immediate' | 'daily' | 'weekly'
  currency: string
  default_search_platform: 'ebay' | 'discogs' | 'both'
  min_record_condition?: string
  min_sleeve_condition?: string
  seller_location_preference?: string
  check_interval_hours?: number
}

export interface CollectionStatus {
  id: string
  item_count: number
  last_sync_at?: string
}

export interface CreateSearchData {
  name: string
  query: string
  platform: 'ebay' | 'discogs' | 'both'
  filters?: SearchFilters
  is_active?: boolean
  check_interval_hours?: number
  min_record_condition?: string
  min_sleeve_condition?: string
  seller_location_preference?: string
}

export interface UpdatePreferencesData {
  email_notifications?: boolean
  notification_frequency?: 'immediate' | 'daily' | 'weekly'
  currency?: string
  default_search_platform?: 'ebay' | 'discogs' | 'both'
  min_record_condition?: string
  min_sleeve_condition?: string
  seller_location_preference?: string
  check_interval_hours?: number
}

// Export alias for backward compatibility
export type Search = SavedSearch
