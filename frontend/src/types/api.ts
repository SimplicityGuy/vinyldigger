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
  // Orchestration fields
  status?: string | null
  results_count: number
  chain_id?: string | null
  template_id?: string | null
  depends_on_search?: string | null
  trigger_conditions?: Record<string, unknown>
  budget_id?: string | null
  estimated_cost_per_result?: number
  optimal_run_times: number[]
  avoid_run_times: number[]
  priority_level?: number
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

// Advanced Search Orchestration Types (Phase 2+)

export interface SearchBudget {
  id: string
  user_id: string
  monthly_limit: number
  current_spent: number
  period_start: string
  period_end: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SearchBudgetSummary {
  budget: SearchBudget | null
  remaining_budget: number | null
  spending_this_month: number
  percentage_used: number | null
  days_remaining: number
}

export interface SearchBudgetCreate {
  monthly_limit: number
  period_start: string
  period_end: string
  is_active?: boolean
}

export interface SearchBudgetUpdate {
  monthly_limit?: number
  period_start?: string
  period_end?: string
  is_active?: boolean
}

export interface SearchTemplate {
  id: string
  name: string
  description: string
  category: string
  template_data: Record<string, unknown>
  parameters: Record<string, unknown>
  is_public: boolean
  created_by: string | null
  usage_count: number
  created_at: string
  updated_at: string
}

export interface SearchTemplateCreate {
  name: string
  description: string
  category: string
  template_data: Record<string, unknown>
  parameters?: Record<string, unknown>
  is_public?: boolean
}

export interface SearchTemplateUpdate {
  name?: string
  description?: string
  category?: string
  template_data?: Record<string, unknown>
  parameters?: Record<string, unknown>
  is_public?: boolean
}

export interface SearchTemplateUse {
  template_id: string
  parameters?: Record<string, unknown>
  name?: string
}

export interface SearchTemplatePreview {
  name: string
  query: string
  platform: string
  filters: Record<string, unknown>
  min_price: number | null
  max_price: number | null
  check_interval_hours: number
}

export interface SearchChain {
  id: string
  user_id: string
  name: string
  description: string | null
  is_active: boolean
  links: SearchChainLink[]
  created_at: string
  updated_at: string
}

export interface SearchChainLink {
  id: string
  chain_id: string
  search_id: string
  order_index: number
  trigger_condition: Record<string, unknown>
  created_at: string
}

export interface SearchChainCreate {
  name: string
  description?: string
  is_active?: boolean
}

export interface SearchChainUpdate {
  name?: string
  description?: string
  is_active?: boolean
}

export interface SearchChainLinkCreate {
  search_id: string
  order_index: number
  trigger_condition?: Record<string, unknown>
}

export interface SearchChainLinkUpdate {
  search_id?: string
  order_index?: number
  trigger_condition?: Record<string, unknown>
}

export interface SearchOrchestrationUpdate {
  depends_on_search?: string
  trigger_conditions?: Record<string, unknown>
  budget_id?: string
  estimated_cost_per_result?: number
  optimal_run_times?: number[]
  avoid_run_times?: number[]
  priority_level?: number
}

export interface SearchScheduleSuggestion {
  current_schedule: string
  suggested_times: number[]
  reasoning: string
  estimated_improvement: string
}

export interface BudgetAlert {
  type: 'budget_critical' | 'budget_warning' | 'budget_underutilized'
  message: string
  severity: 'high' | 'medium' | 'low'
}

export interface SpendingAnalytics {
  total_spent: number
  average_daily: number
  trend: 'over_budget' | 'on_track' | 'under_budget'
  projection: number
  budget_limit: number
  days_elapsed: number
  days_remaining: number
}

// Extended SavedSearch with orchestration fields (deprecated - use SavedSearch directly)
export interface EnhancedSavedSearch extends Omit<SavedSearch, 'optimal_run_times' | 'avoid_run_times'> {
  depends_on_search?: string
  trigger_conditions?: Record<string, unknown>
  budget_id?: string
  estimated_cost_per_result?: number
  optimal_run_times?: number[]
  avoid_run_times?: number[]
  priority_level?: number
}

// Export alias for backward compatibility
export type Search = SavedSearch

export interface TemplateAnalytics {
  total_templates: number
  total_uses: number
  avg_uses_per_template: number
  public_templates: number
  private_templates: number
  avg_parameters_per_template: number
  searches_from_templates: number
  most_used_templates: Array<{
    id: string
    name: string
    category: string
    usage_count: number
    is_public: boolean
  }>
  category_breakdown: Record<string, {
    count: number
    uses: number
  }>
  template_efficiency: {
    templates_with_uses: number
    templates_unused: number
    most_productive_category: string | null
  }
}
