import { memo } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ChevronRight,
  BarChart3,
  TrendingDown,
  Clock,
  Play,
  Package,
  Calendar,
  Timer,
  FileText,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { searchApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'

export const SearchDetailPage = memo(function SearchDetailPage() {
  const { searchId } = useParams<{ searchId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: search, isLoading } = useQuery({
    queryKey: ['search', searchId],
    queryFn: () => searchApi.getSearch(searchId!),
    enabled: !!searchId,
  })

  const runSearchMutation = useMutation({
    mutationFn: () => searchApi.runSearch(searchId!),
    onSuccess: () => {
      toast({
        title: 'Search started',
        description: 'Your search is now running in the background.',
      })
      queryClient.invalidateQueries({ queryKey: ['search', searchId] })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to start search. Please try again.',
        variant: 'destructive',
      })
    },
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!search) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">Search not found</p>
      </div>
    )
  }

  const getPlatformBadge = (platform: string) => {
    const colors = {
      discogs: 'bg-purple-100 text-purple-800',
      ebay: 'bg-blue-100 text-blue-800',
      both: 'bg-gray-100 text-gray-800',
    }
    return colors[platform as keyof typeof colors] || colors.both
  }

  const getFrequencyText = (hours: number) => {
    if (hours === 6) return 'Every 6 hours'
    if (hours === 12) return 'Every 12 hours'
    if (hours === 24) return 'Daily'
    if (hours === 48) return 'Every 2 days'
    if (hours === 72) return 'Every 3 days'
    if (hours === 168) return 'Weekly'
    return `Every ${hours} hours`
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center space-x-2 text-sm text-muted-foreground">
        <Link to="/searches" className="hover:text-foreground transition-colors">
          Searches
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground">{search.name}</span>
      </nav>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">{search.name}</h2>
          <p className="text-muted-foreground mt-1">
            Monitor vinyl records across multiple platforms
          </p>
        </div>
        <Button onClick={() => runSearchMutation.mutate()} disabled={runSearchMutation.isPending}>
          <Play className="h-4 w-4 mr-2" />
          Run Search
        </Button>
      </div>

      {/* Search Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Search Configuration
          </CardTitle>
          <CardDescription>Details about how this search is configured</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="text-sm text-muted-foreground mb-1">Platform</div>
              <Badge className={getPlatformBadge(search.platform)}>
                {search.platform === 'both'
                  ? 'All Platforms'
                  : search.platform.charAt(0).toUpperCase() + search.platform.slice(1)}
              </Badge>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Check Frequency</div>
              <div className="flex items-center gap-2">
                <Timer className="h-4 w-4 text-muted-foreground" />
                <span>{getFrequencyText(search.check_interval_hours)}</span>
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Last Run</div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span>
                  {search.last_run_at ? new Date(search.last_run_at).toLocaleString() : 'Never'}
                </span>
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Check Interval</div>
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span>{search.is_active ? 'Active' : 'Inactive'}</span>
              </div>
            </div>
          </div>

          {/* Search Query */}
          <div className="mt-4 pt-4 border-t">
            <div className="text-sm text-muted-foreground mb-1">Search Query</div>
            <code className="block p-3 bg-muted rounded-md text-sm">{search.query}</code>
          </div>

          {/* Filters */}
          {search.filters && Object.keys(search.filters).length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <div className="text-sm text-muted-foreground mb-2">Active Filters</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(search.filters).map(([key, value]) => (
                  <Badge key={key} variant="secondary">
                    {key}: {String(value)}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate(`/searches/${searchId}/deals`)}
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Multi-Item Deals</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">View Deals</div>
            <p className="text-xs text-muted-foreground">Sellers with multiple items and bulk discounts</p>
          </CardContent>
        </Card>

        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate(`/searches/${searchId}/offers`)}
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Price Comparison</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Compare Offers</div>
            <p className="text-xs text-muted-foreground">Individual listings and price comparisons</p>
          </CardContent>
        </Card>

        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate(`/searches`)}
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">All Searches</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Browse</div>
            <p className="text-xs text-muted-foreground">View all your saved searches</p>
          </CardContent>
        </Card>
      </div>

      {/* Status Information */}
      <Card>
        <CardHeader>
          <CardTitle>Search Status</CardTitle>
          <CardDescription>Current status and execution history</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Last Run</span>
              <span className="text-sm text-muted-foreground">
                {search.last_run_at ? new Date(search.last_run_at).toLocaleString() : 'Never'}
              </span>
            </div>

            {search.is_active ? (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Automatic Execution</span>
                <Badge variant="default">Active</Badge>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Automatic Execution</span>
                <Badge variant="outline">Inactive</Badge>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Created</span>
              <span className="text-sm text-muted-foreground">
                {search.created_at ? new Date(search.created_at).toLocaleDateString() : 'Unknown'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
})
