import { memo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Package, Users, TrendingDown, MapPin, Star, Award, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { searchAnalysisApi } from '@/lib/api'

interface MultiItemDeal {
  seller: {
    id: string | null;
    name: string;
    location: string | null;
    feedback_score: number | null;
  } | null;
  total_items: number;
  wantlist_items: number;
  total_value: number;
  estimated_shipping: number | null;
  total_cost: number;
  potential_savings: number | null;
  deal_score: string;
  item_ids: string[];
}

// Helper function to create URLs
const createListingUrl = (listing: any) => {
  if (listing.platform === 'ebay' && listing.item_data?.item_web_url) {
    return listing.item_data.item_web_url
  }
  return null
}

const createDiscogsReleaseUrl = (listing: any) => {
  if (listing.platform === 'discogs' && listing.item_data?.id) {
    return `https://www.discogs.com/release/${listing.item_data.id}`
  }
  return null
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

  if (dealsLoading || priceLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Multi-Item Deals & Price Comparison</h2>
        <p className="text-muted-foreground">
          Find the best deals by combining multiple items from the same seller
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
                <div
                  key={index}
                  className="border rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                        deal.deal_score === 'EXCELLENT' ? 'bg-green-100 text-green-800' :
                        deal.deal_score === 'VERY_GOOD' ? 'bg-blue-100 text-blue-800' :
                        deal.deal_score === 'GOOD' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
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
          <CardDescription>
            Compare prices across different platforms and sellers
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!priceData?.price_comparisons || priceData.price_comparisons.length === 0 ? (
            <div className="text-center py-8">
              <TrendingDown className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No price comparisons available</p>
            </div>
          ) : (
            <div className="space-y-6">
              {priceData.price_comparisons.map((comparison: {
                item_match: {
                  canonical_title: string;
                  canonical_artist: string;
                  total_matches: number;
                };
                listings: Array<{
                  id: string;
                  platform: string;
                  price: number | null;
                  condition: string | null;
                  seller: {
                    name: string;
                    location: string | null;
                    feedback_score: number | null;
                  } | null;
                  is_in_wantlist: boolean;
                }>;
              }, index: number) => {
                const isExpanded = expandedSections.has(index)
                const visibleListings = isExpanded ? comparison.listings : comparison.listings.slice(0, 1)

                return (
                  <div key={index} className="border rounded-lg">
                    <div
                      className="p-4 cursor-pointer hover:bg-gray-50"
                      onClick={() => toggleSection(index)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium">{comparison.item_match.canonical_title}</h4>
                            {comparison.listings[0]?.platform === 'discogs' && (
                              <a
                                href={createDiscogsReleaseUrl(comparison.listings[0])}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <ExternalLink className="h-3 w-3" />
                                <span className="text-xs">Release Page</span>
                              </a>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground">
                            by {comparison.item_match.canonical_artist}
                          </p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                            <span>{comparison.item_match.total_matches} listings found</span>
                            <span>Best price: {comparison.listings[0]?.price ? `$${comparison.listings[0].price.toFixed(2)}` : 'Price TBD'}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {comparison.listings[0]?.is_in_wantlist && (
                            <Star className="h-4 w-4 text-yellow-500 fill-current" />
                          )}
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
                          {comparison.listings.map((listing, listingIndex: number) => (
                            <div
                              key={listingIndex}
                              className={`flex items-center justify-between p-3 rounded border ${
                                listingIndex === 0 ? 'bg-green-50 border-green-200' : 'bg-gray-50'
                              }`}
                            >
                              <div className="flex items-center gap-4">
                                {listingIndex === 0 && (
                                  <div className="text-green-600 font-medium text-sm">BEST PRICE</div>
                                )}
                                <div className="flex items-center gap-2">
                                  <span className="px-2 py-1 bg-white rounded text-xs font-medium">
                                    {listing.platform}
                                  </span>
                                  {listing.is_in_wantlist && (
                                    <Star className="h-3 w-3 text-yellow-500 fill-current" />
                                  )}
                                </div>
                                <div>
                                  <div className="text-sm">
                                    {listing.seller?.name || 'Unknown Seller'}
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
                                  {listing.seller?.feedback_score && (
                                    <div className="text-xs text-muted-foreground">
                                      {listing.seller.feedback_score.toFixed(1)}% feedback
                                    </div>
                                  )}
                                </div>
                                {createListingUrl(listing) && (
                                  <a
                                    href={createListingUrl(listing)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-600 hover:text-blue-800 p-1"
                                    title="View listing"
                                  >
                                    <ExternalLink className="h-4 w-4" />
                                  </a>
                                )}
                              </div>
                            </div>
                          ))}
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
