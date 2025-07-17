import { memo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart3, TrendingUp, TrendingDown, Users, Star, MapPin, Award, ChevronRight, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { searchAnalysisApi, searchApi } from '@/lib/api'
import type { SearchResult } from '@/types/api'

interface Recommendation {
  id: string
  type: string
  deal_score: string
  score_value: number
  title: string
  description: string
  recommendation_reason: string
  total_items: number
  wantlist_items: number
  total_value: number
  estimated_shipping: number | null
  total_cost: number
  potential_savings: number | null
  seller: {
    id: string | null
    name: string
    location: string | null
    feedback_score: number | null
  } | null
  item_ids: string[]
}

interface Seller {
  id: string | null
  name: string
  location: string | null
  feedback_score: number | null
}

interface MultiItemDeal {
  seller: Seller | null
  total_items: number
  wantlist_items: number
  total_value: number
  estimated_shipping: number | null
  total_cost: number
  potential_savings: number | null
  deal_score: string
  item_ids: string[]
}

interface SellerAnalysis {
  rank: number
  total_items: number
  wantlist_items: number
  total_value: number
  overall_score: number
  estimated_shipping: number | null
  seller: {
    id: string | null
    name: string
    location: string | null
    feedback_score: number | null
  } | null
}

interface ItemData {
  id?: string
  title?: string
  name?: string
  artist?: string
  artists_sort?: string
  price?: number
  current_price?: number
  uri?: string
  item_url?: string
  item_web_url?: string
  [key: string]: unknown
}

// Helper function to extract listing URL from search result
const getListingUrl = (result: SearchResult): string | undefined => {
  const platform = result.platform.toLowerCase()
  const itemData = result.item_data as ItemData

  if (platform === 'ebay' && itemData?.item_web_url) {
    return itemData.item_web_url
  }

  if (platform === 'discogs') {
    // Try different possible URL fields
    if (itemData?.uri) {
      const uri = itemData.uri
      // Check if URI is already a full URL
      if (typeof uri === 'string' && uri.startsWith('http')) {
        return uri
      }
      return `https://www.discogs.com${uri}`
    }
    if (itemData?.item_url) {
      return itemData.item_url
    }
    // If we have a listing ID, construct the marketplace URL
    if (itemData?.id) {
      return `https://www.discogs.com/sell/item/${itemData.id}`
    }
  }

  return undefined
}

// Helper to get item title from search result
const getItemTitle = (result: SearchResult): string => {
  const itemData = result.item_data as ItemData
  return itemData?.title || itemData?.name || 'Unknown Item'
}

// Helper to get artist from search result
const getItemArtist = (result: SearchResult): string => {
  const itemData = result.item_data as ItemData
  return itemData?.artist || itemData?.artists_sort || 'Unknown Artist'
}

// Helper to get price from search result
const getItemPrice = (result: SearchResult): number | null => {
  const itemData = result.item_data as ItemData
  return itemData?.price || itemData?.current_price || null
}

export const SearchDealsPage = memo(function SearchDealsPage() {
  const { searchId } = useParams<{ searchId: string }>()
  const [expandedDealSellers, setExpandedDealSellers] = useState<Set<string>>(new Set())

  const toggleDealSeller = (sellerKey: string) => {
    const newExpanded = new Set(expandedDealSellers)
    if (newExpanded.has(sellerKey)) {
      newExpanded.delete(sellerKey)
    } else {
      newExpanded.add(sellerKey)
    }
    setExpandedDealSellers(newExpanded)
  }

  const { data: search } = useQuery({
    queryKey: ['searches', searchId],
    queryFn: () => searchApi.getSearch(searchId!),
    enabled: !!searchId,
  })

  const { data: analysisData, isLoading } = useQuery({
    queryKey: ['search-analysis', searchId],
    queryFn: () => searchAnalysisApi.getSearchAnalysis(searchId!),
    enabled: !!searchId,
  })

  const { data: dealsData } = useQuery({
    queryKey: ['multi-item-deals', searchId],
    queryFn: () => searchAnalysisApi.getMultiItemDeals(searchId!),
    enabled: !!searchId,
  })

  // Fetch search results for getting item details
  const { data: searchResults } = useQuery({
    queryKey: ['search-results', searchId],
    queryFn: () => searchApi.getSearchResults(searchId!),
    enabled: !!searchId && !!dealsData?.multi_item_deals?.length,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-8" role="status" aria-label="Loading searches">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        <span className="sr-only">Loading searches...</span>
      </div>
    )
  }

  if (!analysisData?.analysis_completed) {
    return (
      <div className="space-y-6">
        {/* Breadcrumb Navigation */}
        <nav className="flex items-center space-x-2 text-sm text-muted-foreground">
          <Link to="/searches" className="hover:text-foreground transition-colors">
            Searches
          </Link>
          <ChevronRight className="h-4 w-4" />
          {search && (
            <>
              <Link
                to={`/searches/${searchId}`}
                className="hover:text-foreground transition-colors"
              >
                {search.name}
              </Link>
              <ChevronRight className="h-4 w-4" />
            </>
          )}
          <span className="text-foreground">Deals</span>
        </nav>

        <div>
          <h2 className="text-3xl font-bold tracking-tight">Search Deals</h2>
          <p className="text-muted-foreground">
            {search
              ? `Analysis for "${search.name}" is still processing or not available`
              : 'Analysis is still processing or not available'}
          </p>
        </div>
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              {analysisData?.message || 'Analysis not yet completed for this search'}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { analysis, recommendations, seller_analyses } = analysisData

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center space-x-2 text-sm text-muted-foreground">
        <Link to="/searches" className="hover:text-foreground transition-colors">
          Searches
        </Link>
        <ChevronRight className="h-4 w-4" />
        {search && (
          <>
            <Link to={`/searches/${searchId}`} className="hover:text-foreground transition-colors">
              {search.name}
            </Link>
            <ChevronRight className="h-4 w-4" />
          </>
        )}
        <span className="text-foreground">Deals</span>
      </nav>

      <div>
        <h2 className="text-3xl font-bold tracking-tight">Search Deals</h2>
        <p className="text-muted-foreground">
          {search
            ? `Analysis for "${search.name}"`
            : 'Comprehensive analysis of search results and recommendations'}
        </p>
      </div>

      {/* Summary Statistics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Results</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analysis.total_results}</div>
            <p className="text-xs text-muted-foreground">From {analysis.total_sellers} sellers</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Want List Matches</CardTitle>
            <Star className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analysis.wantlist_matches}</div>
            <p className="text-xs text-muted-foreground">Items on your want list</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Multi-Item Deals</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analysis.multi_item_sellers}</div>
            <p className="text-xs text-muted-foreground">Sellers with multiple items</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Price Range</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${analysis.min_price?.toFixed(2)} - ${analysis.max_price?.toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">Avg: ${analysis.avg_price?.toFixed(2)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Multi-Item Deals */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Multi-Item Deals
          </CardTitle>
          <CardDescription>
            Sellers with multiple items where you can save on shipping costs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!dealsData?.multi_item_deals || dealsData.multi_item_deals.length === 0 ? (
            <div className="text-center py-8">
              <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No multi-item deals found</p>
              <p className="text-sm text-muted-foreground mt-2">
                Run a search to find sellers with multiple items from your want list
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {dealsData.multi_item_deals.map((deal: MultiItemDeal, index: number) => {
                const sellerKey = deal.seller?.name || `deal-${index}`
                const isExpanded = expandedDealSellers.has(sellerKey)
                const itemsInDeal = searchResults?.filter((result: SearchResult) => deal.item_ids.includes(result.id)) || []

                return (
                  <div key={index} className="border rounded-lg overflow-hidden">
                    <div
                      className="p-4 space-y-3 cursor-pointer hover:bg-gray-50 transition-colors"
                      onClick={() => toggleDealSeller(sellerKey)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div
                            className={`px-3 py-1 rounded-full text-sm font-medium ${
                              deal.deal_score === 'EXCELLENT'
                                ? 'bg-green-100 text-green-800'
                                : deal.deal_score === 'VERY_GOOD'
                                  ? 'bg-blue-100 text-blue-800'
                                  : deal.deal_score === 'GOOD'
                                    ? 'bg-yellow-100 text-yellow-800'
                                    : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {deal.deal_score.replace('_', ' ')} DEAL
                          </div>
                          {deal.seller && (
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{deal.seller.name}</span>
                              {deal.seller.location && (
                                <span className="text-muted-foreground flex items-center gap-1">
                                  <MapPin className="h-3 w-3" />
                                  {deal.seller.location}
                                </span>
                              )}
                              {deal.seller.feedback_score && (
                                <span className="text-muted-foreground flex items-center gap-1">
                                  <Award className="h-3 w-3" />
                                  {deal.seller.feedback_score.toFixed(1)}%
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {isExpanded ? (
                            <ChevronUp className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <div className="text-muted-foreground">Total Items</div>
                          <div className="font-medium">{deal.total_items}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Want List Items</div>
                          <div className="font-medium text-green-600">{deal.wantlist_items}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Items Value</div>
                          <div className="font-medium">${deal.total_value.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Est. Shipping</div>
                          <div className="font-medium">
                            {deal.estimated_shipping ? `$${deal.estimated_shipping.toFixed(2)}` : 'TBD'}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t">
                        <div className="text-lg font-semibold">
                          Total: ${deal.total_cost.toFixed(2)}
                        </div>
                        {deal.potential_savings && deal.potential_savings > 0 && (
                          <div className="flex items-center gap-1 text-green-600 font-medium">
                            <TrendingDown className="h-4 w-4" />
                            Save ${deal.potential_savings.toFixed(2)} on shipping
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Expandable Items Section */}
                    {isExpanded && (
                      <div className="border-t bg-gray-50">
                        <div className="p-4">
                          <h5 className="font-medium text-sm mb-3">Items in this deal:</h5>
                          <div className="space-y-2">
                            {itemsInDeal.length === 0 ? (
                              <p className="text-sm text-muted-foreground">Loading item details...</p>
                            ) : (
                              itemsInDeal.map((item) => {
                                const listingUrl = getListingUrl(item)
                                const price = getItemPrice(item)

                                return (
                                  <div
                                    key={item.id}
                                    className="flex items-center justify-between p-3 bg-white rounded border"
                                  >
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2">
                                        {item.is_in_wantlist && (
                                          <Star className="h-4 w-4 text-yellow-500 fill-current" aria-label="In your wantlist" />
                                        )}
                                        <span className="font-medium text-sm">{getItemTitle(item)}</span>
                                      </div>
                                      <div className="text-xs text-muted-foreground mt-1">
                                        by {getItemArtist(item)}
                                      </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                      <div className="text-right">
                                        <div className="text-sm font-medium">
                                          {price ? `$${price.toFixed(2)}` : 'Price TBD'}
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                          {item.platform.charAt(0).toUpperCase() + item.platform.slice(1).toLowerCase()}
                                        </div>
                                      </div>
                                      {listingUrl && (
                                        <a
                                          href={listingUrl}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="text-blue-600 hover:text-blue-800 p-2 rounded hover:bg-blue-50 transition-colors flex items-center gap-1"
                                          title="View listing"
                                          onClick={(e) => e.stopPropagation()}
                                        >
                                          <ExternalLink className="h-4 w-4" />
                                          <span className="text-xs">View</span>
                                        </a>
                                      )}
                                    </div>
                                  </div>
                                )
                              })
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Other Recommendations */}
      {recommendations.filter((rec: Recommendation) => rec.type !== 'MULTI_ITEM').length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Other Recommendations</CardTitle>
            <CardDescription>Additional deals and opportunities</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recommendations.filter((rec: Recommendation) => rec.type !== 'MULTI_ITEM').map((rec: Recommendation) => (
                <div key={rec.id} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          rec.deal_score === 'EXCELLENT'
                            ? 'bg-green-100 text-green-800'
                            : rec.deal_score === 'VERY_GOOD'
                              ? 'bg-blue-100 text-blue-800'
                              : rec.deal_score === 'GOOD'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {rec.deal_score.replace('_', ' ')}
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {rec.type.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="text-sm font-medium">Score: {rec.score_value.toFixed(0)}%</div>
                  </div>

                  <div>
                    <h4 className="font-medium">{rec.title}</h4>
                    <p className="text-sm text-muted-foreground">{rec.description}</p>
                    <p className="text-sm text-blue-600 mt-1">{rec.recommendation_reason}</p>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4">
                      <span>{rec.total_items} items</span>
                      {rec.wantlist_items > 0 && (
                        <span className="text-green-600">{rec.wantlist_items} want list items</span>
                      )}
                      {rec.seller && (
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          <span>{rec.seller.name}</span>
                          {rec.seller.location && (
                            <span className="text-muted-foreground">({rec.seller.location})</span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="font-medium">${rec.total_cost.toFixed(2)} total</div>
                      {rec.potential_savings && rec.potential_savings > 0 && (
                        <div className="text-green-600 text-xs">
                          Save ${rec.potential_savings.toFixed(2)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top Sellers */}
      <Card>
        <CardHeader>
          <CardTitle>Top Sellers</CardTitle>
          <CardDescription>Sellers ranked by overall score</CardDescription>
        </CardHeader>
        <CardContent>
          {seller_analyses.length === 0 ? (
            <p className="text-muted-foreground">No seller analysis available</p>
          ) : (
            <div className="space-y-3">
              {seller_analyses.slice(0, 10).map((seller: SellerAnalysis) => (
                <div
                  key={seller.seller?.id || `seller-${seller.rank}`}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 bg-muted rounded-full text-sm font-medium">
                      #{seller.rank}
                    </div>
                    <div>
                      <div className="font-medium">{seller.seller?.name || 'Unknown Seller'}</div>
                      <div className="text-sm text-muted-foreground flex items-center gap-4">
                        <span>{seller.total_items} items</span>
                        {seller.wantlist_items > 0 && (
                          <span className="text-green-600">{seller.wantlist_items} want list</span>
                        )}
                        {seller.seller?.location && <span>{seller.seller.location}</span>}
                        {seller.seller?.feedback_score && (
                          <div className="flex items-center gap-1">
                            <Award className="h-3 w-3" />
                            <span>{seller.seller.feedback_score.toFixed(1)}%</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium">{seller.overall_score.toFixed(0)}% score</div>
                    <div className="text-sm text-muted-foreground">
                      ${seller.total_value.toFixed(2)}
                      {seller.estimated_shipping && (
                        <span> + ${seller.estimated_shipping.toFixed(2)} shipping</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
})
