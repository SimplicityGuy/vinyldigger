import { memo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart3, TrendingUp, Users, Star, MapPin, Award } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { searchAnalysisApi } from '@/lib/api'

interface Recommendation {
  id: string;
  type: string;
  deal_score: string;
  score_value: number;
  title: string;
  description: string;
  recommendation_reason: string;
  total_items: number;
  wantlist_items: number;
  total_value: number;
  estimated_shipping: number | null;
  total_cost: number;
  potential_savings: number | null;
  seller: {
    id: string | null;
    name: string;
    location: string | null;
    feedback_score: number | null;
  } | null;
  item_ids: string[];
}

interface SellerAnalysis {
  rank: number;
  total_items: number;
  wantlist_items: number;
  total_value: number;
  overall_score: number;
  estimated_shipping: number | null;
  seller: {
    id: string | null;
    name: string;
    location: string | null;
    feedback_score: number | null;
  } | null;
}

export const SearchAnalysisPage = memo(function SearchAnalysisPage() {
  const { searchId } = useParams<{ searchId: string }>()

  const { data: analysisData, isLoading } = useQuery({
    queryKey: ['search-analysis', searchId],
    queryFn: () => searchAnalysisApi.getSearchAnalysis(searchId!),
    enabled: !!searchId,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!analysisData?.analysis_completed) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Search Analysis</h2>
          <p className="text-muted-foreground">Analysis is still processing or not available</p>
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
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Search Analysis</h2>
        <p className="text-muted-foreground">
          Comprehensive analysis of search results and recommendations
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
            <p className="text-xs text-muted-foreground">
              From {analysis.total_sellers} sellers
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Want List Matches</CardTitle>
            <Star className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analysis.wantlist_matches}</div>
            <p className="text-xs text-muted-foreground">
              Items on your want list
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Multi-Item Deals</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analysis.multi_item_sellers}</div>
            <p className="text-xs text-muted-foreground">
              Sellers with multiple items
            </p>
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
            <p className="text-xs text-muted-foreground">
              Avg: ${analysis.avg_price?.toFixed(2)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Deal Recommendations</CardTitle>
          <CardDescription>Smart recommendations based on your preferences</CardDescription>
        </CardHeader>
        <CardContent>
          {recommendations.length === 0 ? (
            <p className="text-muted-foreground">No recommendations available</p>
          ) : (
            <div className="space-y-4">
              {recommendations.map((rec: Recommendation) => (
                <div
                  key={rec.id}
                  className="border rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`px-2 py-1 rounded text-xs font-medium ${
                        rec.deal_score === 'EXCELLENT' ? 'bg-green-100 text-green-800' :
                        rec.deal_score === 'VERY_GOOD' ? 'bg-blue-100 text-blue-800' :
                        rec.deal_score === 'GOOD' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {rec.deal_score.replace('_', ' ')}
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {rec.type.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="text-sm font-medium">
                      Score: {rec.score_value.toFixed(0)}%
                    </div>
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
                        <span className="text-green-600">
                          {rec.wantlist_items} want list items
                        </span>
                      )}
                      {rec.seller && (
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          <span>{rec.seller.name}</span>
                          {rec.seller.location && (
                            <span className="text-muted-foreground">
                              ({rec.seller.location})
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="font-medium">
                        ${rec.total_cost.toFixed(2)} total
                      </div>
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
          )}
        </CardContent>
      </Card>

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
                          <span className="text-green-600">
                            {seller.wantlist_items} want list
                          </span>
                        )}
                        {seller.seller?.location && (
                          <span>{seller.seller.location}</span>
                        )}
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
                    <div className="font-medium">
                      {seller.overall_score.toFixed(0)}% score
                    </div>
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
