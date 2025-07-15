import { memo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Package,
  Users,
  TrendingDown,
  MapPin,
  Star,
  Award,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  ChevronRight,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { searchAnalysisApi, searchApi } from '@/lib/api'

interface Seller {
  id: string | null
  name: string
  location: string | null
  feedback_score: number | null
}

interface ListingItemData {
  id?: string
  item_web_url?: string
  release_id?: string
  resource_url?: string
  title?: string
  artist?: string
  year?: number
  item_url?: string
  seller?: {
    id?: string
    username?: string
    url?: string
  }
  [key: string]: unknown
}

interface Listing {
  id: string
  platform: string
  price: number | null
  condition: string | null
  seller: Seller | null
  is_in_wantlist: boolean
  shipping_price?: number
  item_data?: ListingItemData
}

interface ItemMatch {
  canonical_title: string
  canonical_artist: string
  total_matches: number
}

interface PriceComparison {
  item_match: ItemMatch
  listings: Listing[]
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

// Helper function to create URLs
const createListingUrl = (listing: Listing): string | undefined => {
  const platform = listing.platform.toLowerCase()

  if (platform === 'ebay' && listing.item_data?.item_web_url) {
    return listing.item_data.item_web_url
  }
  if (platform === 'discogs') {
    // Try different possible URL fields
    if (listing.item_data?.uri) {
      const uri = listing.item_data.uri
      // Check if URI is already a full URL
      if (typeof uri === 'string' && uri.startsWith('http')) {
        return uri
      }
      return `https://www.discogs.com${uri}`
    }
    if (listing.item_data?.item_url) {
      return listing.item_data.item_url
    }
    // If we have a listing ID, construct the marketplace URL
    if (listing.item_data?.id) {
      return `https://www.discogs.com/sell/item/${listing.item_data.id}`
    }
  }
  return undefined
}

const createDiscogsReleaseUrl = (listing: Listing): string | undefined => {
  const platform = listing.platform.toLowerCase()
  if (platform === 'discogs' && listing.item_data) {
    const itemData = listing.item_data
    // First check if we have release_id directly
    if (itemData.release_id) {
      return `https://www.discogs.com/release/${itemData.release_id}`
    }
    // Check if it's a release or master based on the resource_url
    if (itemData.resource_url) {
      if (itemData.resource_url.includes('/releases/')) {
        return `https://www.discogs.com/release/${itemData.id}`
      } else if (itemData.resource_url.includes('/masters/')) {
        return `https://www.discogs.com/master/${itemData.id}`
      }
    }
    // Fallback to release URL
    if (itemData.id) {
      return `https://www.discogs.com/release/${itemData.id}`
    }
  }
  return undefined
}

const createSellerUrl = (listing: Listing): string | undefined => {
  const platform = listing.platform.toLowerCase()
  if (platform === 'discogs') {
    // Try seller URL from item_data first
    if (listing.item_data?.seller?.url) {
      return listing.item_data.seller.url
    }
    // Try seller username to construct URL
    if (listing.item_data?.seller?.username) {
      return `https://www.discogs.com/seller/${listing.item_data.seller.username}`
    }
    // Fallback to main seller object
    if (listing.seller?.name) {
      return `https://www.discogs.com/seller/${listing.seller.name}`
    }
  }
  if (platform === 'ebay' && listing.seller?.name) {
    return `https://www.ebay.com/usr/${listing.seller.name}`
  }
  return undefined
}

// Helper to get seller name from listing data
const getSellerName = (listing: Listing): string => {
  // First check if we have seller info in the main seller object
  if (listing.seller?.name) {
    return listing.seller.name
  }
  // Then check in item_data for marketplace seller info
  if (listing.item_data?.seller?.username) {
    return listing.item_data.seller.username
  }
  return 'Unknown Seller'
}

export const SearchDealsPage = memo(function SearchDealsPage() {
  const { searchId } = useParams<{ searchId: string }>()
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set())

  const toggleSection = (index: number) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedSections(newExpanded)
  }

  const { data: searchData, isLoading: searchLoading } = useQuery({
    queryKey: ['search', searchId],
    queryFn: () => searchApi.getSearch(searchId!),
    enabled: !!searchId,
  })

  const { data: dealsData, isLoading: dealsLoading } = useQuery({
    queryKey: ['multi-item-deals', searchId],
    queryFn: () => searchAnalysisApi.getMultiItemDeals(searchId!),
    enabled: !!searchId,
  })

  const { data: priceData, isLoading: priceLoading } = useQuery({
    queryKey: ['price-comparison', searchId],
    queryFn: () => searchAnalysisApi.getPriceComparison(searchId!),
    enabled: !!searchId,
  })

  if (searchLoading || dealsLoading || priceLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center space-x-2 text-sm text-muted-foreground">
        <Link to="/searches" className="hover:text-foreground transition-colors">
          Searches
        </Link>
        <ChevronRight className="h-4 w-4" />
        {searchData && (
          <>
            <Link to={`/searches/${searchId}`} className="hover:text-foreground transition-colors">
              {searchData.name}
            </Link>
            <ChevronRight className="h-4 w-4" />
          </>
        )}
        <span className="text-foreground">Deals</span>
      </nav>

      <div>
        <h2 className="text-3xl font-bold tracking-tight">Multi-Item Deals & Price Comparison</h2>
        <p className="text-muted-foreground">
          {searchData
            ? `Results for "${searchData.name}"`
            : 'Find the best deals by combining multiple items from the same seller'}
        </p>
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
              <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No multi-item deals found</p>
              <p className="text-sm text-muted-foreground mt-2">
                Run a search to find sellers with multiple items from your want list
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {dealsData.multi_item_deals.map((deal: MultiItemDeal, index: number) => (
                <div key={index} className="border rounded-lg p-4 space-y-3">
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
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Price Comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingDown className="h-5 w-5" />
            Price Comparison
          </CardTitle>
          <CardDescription>Compare prices across different platforms and sellers</CardDescription>
        </CardHeader>
        <CardContent>
          {!priceData?.price_comparisons || priceData.price_comparisons.length === 0 ? (
            <div className="text-center py-8">
              <TrendingDown className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No price comparisons available</p>
            </div>
          ) : (
            <div className="space-y-6">
              {priceData.price_comparisons
                // Sort comparisons so that items in wantlist appear first
                .sort((a: PriceComparison, b: PriceComparison) => {
                  const aHasWantlist = a.listings.some((l) => l.is_in_wantlist)
                  const bHasWantlist = b.listings.some((l) => l.is_in_wantlist)
                  if (aHasWantlist && !bHasWantlist) return -1
                  if (!aHasWantlist && bHasWantlist) return 1
                  return 0
                })
                .map((comparison: PriceComparison, index: number) => {
                const isExpanded = expandedSections.has(index)

                return (
                  <div key={index} className="border rounded-lg">
                    <div
                      className="p-4 cursor-pointer hover:bg-gray-50"
                      onClick={() => toggleSection(index)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            {comparison.listings.some((l) => l.is_in_wantlist) && (
                              <span title="In your wantlist" className="flex items-center gap-1">
                                <Star className="h-4 w-4 text-yellow-500 fill-current" />
                                <span className="text-xs text-yellow-600 font-medium">WANT LIST</span>
                              </span>
                            )}
                            <h4 className="font-medium">{comparison.item_match.canonical_title}</h4>
                            {(() => {
                              // Find any Discogs listing to get the release link
                              const discogsListing = comparison.listings.find(
                                (listing) => listing.platform.toLowerCase() === 'discogs'
                              )
                              if (discogsListing) {
                                const releaseUrl = createDiscogsReleaseUrl(discogsListing)
                                if (releaseUrl) {
                                  return (
                                    <a
                                      href={releaseUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <ExternalLink className="h-3 w-3" />
                                      <span className="text-xs">Discogs</span>
                                    </a>
                                  )
                                }
                              }
                              return null
                            })()}
                          </div>
                          <p className="text-sm text-muted-foreground">
                            by {comparison.item_match.canonical_artist || 'Unknown Artist'}
                          </p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                            <span>{comparison.item_match.total_matches} listings found</span>
                            <span>
                              Best price:{' '}
                              {comparison.listings[0]?.price
                                ? `$${comparison.listings[0].price.toFixed(2)}`
                                : 'Price TBD'}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {isExpanded ? (
                            <ChevronUp className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          )}
                        </div>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="border-t">
                        <div className="p-4 space-y-2">
                          {comparison.listings
                            // Sort listings so wantlist items appear first
                            .sort((a, b) => {
                              if (a.is_in_wantlist && !b.is_in_wantlist) return -1
                              if (!a.is_in_wantlist && b.is_in_wantlist) return 1
                              // Then sort by price
                              const priceA = a.price ?? Number.MAX_VALUE
                              const priceB = b.price ?? Number.MAX_VALUE
                              return priceA - priceB
                            })
                            .map((listing, listingIndex: number) => {
                            const sellerName = getSellerName(listing)
                            const sellerUrl = createSellerUrl(listing)
                            const listingUrl = createListingUrl(listing)

                            // Find the listing with the lowest price
                            const lowestPriceListing = comparison.listings.reduce((min, current) => {
                              const minPrice = min.price ?? Number.MAX_VALUE
                              const currentPrice = current.price ?? Number.MAX_VALUE
                              return currentPrice < minPrice ? current : min
                            })
                            const isLowestPrice = listing.id === lowestPriceListing.id

                            return (
                              <div
                                key={listingIndex}
                                className={`flex items-center justify-between p-3 rounded border ${
                                  listing.is_in_wantlist
                                    ? 'bg-yellow-50 border-yellow-200'
                                    : isLowestPrice
                                    ? 'bg-green-50 border-green-200'
                                    : 'bg-gray-50'
                                }`}
                              >
                                <div className="flex items-center gap-4">
                                  {isLowestPrice && (
                                    <div className="text-green-600 font-medium text-sm">
                                      BEST PRICE
                                    </div>
                                  )}
                                  <div className="flex items-center gap-2">
                                    <span className="px-2 py-1 bg-white rounded text-xs font-medium">
                                      {listing.platform.charAt(0).toUpperCase() + listing.platform.slice(1).toLowerCase()}
                                    </span>
                                    {listing.is_in_wantlist ? (
                                      <span className="flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">
                                        <Star className="h-3 w-3 fill-current" />
                                        WANT LIST
                                      </span>
                                    ) : (
                                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                                        NEW DISCOVERY
                                      </span>
                                    )}
                                  </div>
                                  <div>
                                    <div className="text-sm flex items-center gap-2">
                                      {sellerUrl ? (
                                        <a
                                          href={sellerUrl}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                                          onClick={(e) => e.stopPropagation()}
                                        >
                                          {sellerName}
                                          <ExternalLink className="h-3 w-3" />
                                        </a>
                                      ) : (
                                        <span className="font-medium">{sellerName}</span>
                                      )}
                                    </div>
                                    {listing.seller?.location && (
                                      <div className="text-xs text-muted-foreground">
                                        {listing.seller.location}
                                      </div>
                                    )}
                                  </div>
                                  {listing.condition && (
                                    <div className="text-sm text-muted-foreground">
                                      Condition: {listing.condition}
                                    </div>
                                  )}
                                </div>
                                <div className="text-right flex items-center gap-2">
                                  <div>
                                    <div className="font-medium">
                                      {listing.price ? `$${listing.price.toFixed(2)}` : 'Price TBD'}
                                    </div>
                                    {listing.shipping_price !== undefined &&
                                      listing.shipping_price !== null && (
                                        <div className="text-xs text-muted-foreground">
                                          + ${listing.shipping_price.toFixed(2)} shipping
                                        </div>
                                      )}
                                    {listing.seller?.feedback_score && (
                                      <div className="text-xs text-muted-foreground">
                                        {listing.seller.feedback_score.toFixed(1)}% feedback
                                      </div>
                                    )}
                                  </div>
                                  {listingUrl ? (
                                    <a
                                      href={listingUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-600 hover:text-blue-800 p-2 rounded hover:bg-blue-50 transition-colors flex items-center gap-1"
                                      title="View listing"
                                    >
                                      <ExternalLink className="h-4 w-4" />
                                      <span className="text-xs">View</span>
                                    </a>
                                  ) : (
                                    <div className="text-xs text-muted-foreground p-2">No link</div>
                                  )}
                                </div>
                              </div>
                            )
                          })}
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
    </div>
  )
})
