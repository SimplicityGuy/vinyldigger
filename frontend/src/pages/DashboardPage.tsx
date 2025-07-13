import { memo, useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Package, Heart, RefreshCw, Check, Loader2, Minus, Search, TrendingUp, Clock, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { collectionApi, oauthApi, searchApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Link } from 'react-router-dom'
import type { SavedSearch } from '@/types/api'

export const DashboardPage = memo(function DashboardPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncType, setSyncType] = useState<'both' | 'collection' | 'wantlist' | null>(null)
  const syncStartTimeRef = useRef<number | null>(null)

  const { data: collectionStatus } = useQuery({
    queryKey: ['collection-status'],
    queryFn: collectionApi.getCollectionStatus,
    refetchInterval: isSyncing ? 3000 : 30000, // Poll every 3 seconds while syncing, 30 seconds otherwise
    staleTime: isSyncing ? 0 : 5000, // Consider data stale immediately while syncing
  })

  const { data: wantListStatus } = useQuery({
    queryKey: ['wantlist-status'],
    queryFn: collectionApi.getWantListStatus,
    refetchInterval: isSyncing ? 3000 : 30000, // Poll every 3 seconds while syncing, 30 seconds otherwise
    staleTime: isSyncing ? 0 : 5000, // Consider data stale immediately while syncing
  })

  const { data: discogsOAuthStatus } = useQuery({
    queryKey: ['oauth-status', 'discogs'],
    queryFn: () => oauthApi.getOAuthStatus('discogs'),
  })

  const { data: searches = [] } = useQuery({
    queryKey: ['searches'],
    queryFn: searchApi.getSearches,
  })

  // Track completion status
  const collectionItemCount = collectionStatus?.item_count || 0
  const wantListItemCount = wantListStatus?.item_count || 0

  const completionStatus = {
    discogsConnected: discogsOAuthStatus?.is_authorized || false,
    collectionSynced: collectionItemCount > 0,
    wantListSynced: wantListItemCount > 0,
    bothSynced: collectionItemCount > 0 && wantListItemCount > 0,
    eitherSynced: collectionItemCount > 0 || wantListItemCount > 0,
    searchCreated: searches.length > 0,
  }

  const allTasksCompleted =
    completionStatus.discogsConnected &&
    completionStatus.bothSynced &&
    completionStatus.searchCreated

  const syncAllMutation = useMutation({
    mutationFn: collectionApi.syncCollection,
    onMutate: () => {
      setIsSyncing(true)
      setSyncType('both')
      syncStartTimeRef.current = Date.now()
      // Invalidate queries to get fresh data
      queryClient.invalidateQueries({ queryKey: ['collection-status'] })
      queryClient.invalidateQueries({ queryKey: ['wantlist-status'] })
    },
    onSuccess: () => {
      toast({
        title: 'Sync started',
        description: 'Your collection and want list are being synced with Discogs.',
      })
      // Fallback timeout in case sync completion detection fails
      setTimeout(() => {
        if (isSyncing) {
          setIsSyncing(false)
          setSyncType(null)
          syncStartTimeRef.current = null
          // Force a final refresh
          queryClient.invalidateQueries({ queryKey: ['collection-status'] })
          queryClient.invalidateQueries({ queryKey: ['wantlist-status'] })
        }
      }, 60000) // Extended to 60 seconds
    },
    onError: () => {
      setIsSyncing(false)
      setSyncType(null)
      syncStartTimeRef.current = null
      toast({
        title: 'Sync failed',
        description: 'Failed to start collection and want list sync.',
        variant: 'destructive',
      })
    },
  })

  const syncCollectionMutation = useMutation({
    mutationFn: collectionApi.syncCollectionOnly,
    onMutate: () => {
      setIsSyncing(true)
      setSyncType('collection')
      syncStartTimeRef.current = Date.now()
      queryClient.invalidateQueries({ queryKey: ['collection-status'] })
    },
    onSuccess: () => {
      toast({
        title: 'Sync started',
        description: 'Your collection is being synced with Discogs.',
      })
      setTimeout(() => {
        if (isSyncing) {
          setIsSyncing(false)
          setSyncType(null)
          syncStartTimeRef.current = null
          queryClient.invalidateQueries({ queryKey: ['collection-status'] })
        }
      }, 60000)
    },
    onError: () => {
      setIsSyncing(false)
      setSyncType(null)
      syncStartTimeRef.current = null
      toast({
        title: 'Sync failed',
        description: 'Failed to start collection sync.',
        variant: 'destructive',
      })
    },
  })

  const syncWantListMutation = useMutation({
    mutationFn: collectionApi.syncWantListOnly,
    onMutate: () => {
      setIsSyncing(true)
      setSyncType('wantlist')
      syncStartTimeRef.current = Date.now()
      queryClient.invalidateQueries({ queryKey: ['wantlist-status'] })
    },
    onSuccess: () => {
      toast({
        title: 'Sync started',
        description: 'Your want list is being synced with Discogs.',
      })
      setTimeout(() => {
        if (isSyncing) {
          setIsSyncing(false)
          setSyncType(null)
          syncStartTimeRef.current = null
          queryClient.invalidateQueries({ queryKey: ['wantlist-status'] })
        }
      }, 60000)
    },
    onError: () => {
      setIsSyncing(false)
      setSyncType(null)
      syncStartTimeRef.current = null
      toast({
        title: 'Sync failed',
        description: 'Failed to start want list sync.',
        variant: 'destructive',
      })
    },
  })

  // Improved sync completion detection
  useEffect(() => {
    if (!isSyncing || !syncStartTimeRef.current) return

    const syncStartTime = syncStartTimeRef.current
    const currentTime = Date.now()

    // Only check for completion if sync has been running for at least 5 seconds
    if (currentTime - syncStartTime < 5000) return

    const collectionLastSync = collectionStatus?.last_sync_at ? new Date(collectionStatus.last_sync_at).getTime() : 0
    const wantListLastSync = wantListStatus?.last_sync_at ? new Date(wantListStatus.last_sync_at).getTime() : 0

    let syncCompleted = false

    if (syncType === 'both') {
      // For both sync, check if either has been synced after the start time
      syncCompleted = collectionLastSync > syncStartTime || wantListLastSync > syncStartTime
    } else if (syncType === 'collection') {
      syncCompleted = collectionLastSync > syncStartTime
    } else if (syncType === 'wantlist') {
      syncCompleted = wantListLastSync > syncStartTime
    }

    if (syncCompleted) {
      setIsSyncing(false)
      setSyncType(null)
      syncStartTimeRef.current = null

      // Show success message
      toast({
        title: 'Sync completed',
        description: 'Your data has been successfully synced with Discogs.',
      })

      // Force a final refresh to ensure UI is updated
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['collection-status'] })
        queryClient.invalidateQueries({ queryKey: ['wantlist-status'] })
      }, 1000)
    }
  }, [isSyncing, syncType, collectionStatus?.last_sync_at, wantListStatus?.last_sync_at, toast, queryClient])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Overview of your vinyl collection and recent activity
        </p>
      </div>

      {/* Sync Progress Indicator */}
      {isSyncing && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="flex items-center gap-4 py-4">
            <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
            <div className="flex-1">
              <p className="font-medium text-blue-900">
                Syncing{' '}
                {syncType === 'collection'
                  ? 'collection'
                  : syncType === 'wantlist'
                    ? 'want list'
                    : 'collection and want list'}{' '}
                with Discogs...
              </p>
              <p className="text-sm text-blue-700">
                This may take a few minutes depending on the size
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Enhanced Stats Grid */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Collection</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{collectionStatus?.item_count || 0}</div>
            <p className="text-xs text-muted-foreground">
              Records in your collection
              {collectionStatus?.last_sync_at && (
                <span className="block mt-1 text-green-600">
                  ✓ Synced {new Date(collectionStatus.last_sync_at).toLocaleDateString()}
                </span>
              )}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Want List</CardTitle>
            <Heart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{wantListStatus?.item_count || 0}</div>
            <p className="text-xs text-muted-foreground">
              Records on your want list
              {wantListStatus?.last_sync_at && (
                <span className="block mt-1 text-green-600">
                  ✓ Synced {new Date(wantListStatus.last_sync_at).toLocaleDateString()}
                </span>
              )}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Saved Searches</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{searches.length}</div>
            <p className="text-xs text-muted-foreground">
              Active searches monitoring
              {searches.length > 0 && (
                <Link to="/searches" className="block mt-1 text-blue-600 hover:text-blue-800">
                  View all →
                </Link>
              )}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {allTasksCompleted ? '✓' : `${Object.values(completionStatus).filter(Boolean).length}/4`}
            </div>
            <p className="text-xs text-muted-foreground">
              {allTasksCompleted ? 'All setup complete' : 'Setup progress'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      {(searches.length > 0 || completionStatus.eitherSynced) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Recent Activity
            </CardTitle>
            <CardDescription>Your latest searches and sync activity</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {searches.slice(0, 3).map((search: SavedSearch) => (
                <div key={search.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Search className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{search.name}</span>
                    </div>
                    <span className="text-sm text-muted-foreground">•</span>
                    <span className="text-sm text-muted-foreground">
                      {search.last_run_at
                        ? `Last run ${new Date(search.last_run_at).toLocaleDateString()}`
                        : 'Never run'
                      }
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link to={`/searches/${search.id}/analysis`}>
                      <Button size="sm" variant="outline" className="gap-1">
                        <TrendingUp className="h-3 w-3" />
                        View
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}

              {searches.length === 0 && (
                <div className="text-center py-6">
                  <Search className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No searches yet</p>
                  <Link to="/searches">
                    <Button size="sm" className="mt-2">Create your first search</Button>
                  </Link>
                </div>
              )}

              {searches.length > 3 && (
                <div className="pt-2 border-t">
                  <Link to="/searches" className="flex items-center justify-center gap-2 text-sm text-blue-600 hover:text-blue-800">
                    View all {searches.length} searches
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks to manage your collection</CardDescription>
        </CardHeader>
        <CardContent>
          {discogsOAuthStatus?.is_authorized ? (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => syncAllMutation.mutate()}
                  disabled={syncAllMutation.isPending || isSyncing}
                  className="gap-2"
                >
                  <RefreshCw
                    className={`h-4 w-4 ${syncAllMutation.isPending || (isSyncing && syncType === 'both') ? 'animate-spin' : ''}`}
                  />
                  {syncAllMutation.isPending || (isSyncing && syncType === 'both')
                    ? 'Syncing...'
                    : 'Sync All'}
                </Button>
                <Button
                  onClick={() => syncCollectionMutation.mutate()}
                  disabled={syncCollectionMutation.isPending || isSyncing}
                  variant="outline"
                  className="gap-2"
                >
                  <Package
                    className={`h-4 w-4 ${syncCollectionMutation.isPending || (isSyncing && syncType === 'collection') ? 'animate-spin' : ''}`}
                  />
                  {syncCollectionMutation.isPending || (isSyncing && syncType === 'collection')
                    ? 'Syncing...'
                    : 'Sync Collection Only'}
                </Button>
                <Button
                  onClick={() => syncWantListMutation.mutate()}
                  disabled={syncWantListMutation.isPending || isSyncing}
                  variant="outline"
                  className="gap-2"
                >
                  <Heart
                    className={`h-4 w-4 ${syncWantListMutation.isPending || (isSyncing && syncType === 'wantlist') ? 'animate-spin' : ''}`}
                  />
                  {syncWantListMutation.isPending || (isSyncing && syncType === 'wantlist')
                    ? 'Syncing...'
                    : 'Sync Want List Only'}
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                Sync your Discogs collection and want list to find matches in your searches
              </p>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-4 mb-2">
                <Button disabled className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  Sync Collection & Want List
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                Connect your Discogs account in{' '}
                <Link to="/settings" className="text-primary underline">
                  Settings
                </Link>{' '}
                to sync your collection and want list.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Setup Notice - Show only if not all tasks are completed */}
      {!allTasksCompleted && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader className="flex flex-row items-center gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <CardTitle className="text-lg">Get Started</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">
              To start using VinylDigger, complete these steps:
            </p>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                {completionStatus.discogsConnected ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
                )}
                <span
                  className={completionStatus.discogsConnected ? 'text-green-700 line-through' : ''}
                >
                  Connect your Discogs account in{' '}
                  <Link to="/settings" className="text-primary underline">
                    Settings
                  </Link>
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                {completionStatus.bothSynced ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : completionStatus.eitherSynced ? (
                  <Minus className="h-4 w-4 text-yellow-600" />
                ) : (
                  <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
                )}
                <span
                  className={
                    completionStatus.bothSynced
                      ? 'text-green-700 line-through'
                      : completionStatus.eitherSynced
                        ? 'text-yellow-700'
                        : ''
                  }
                >
                  Sync your collection and want list using the button above
                  {completionStatus.eitherSynced && !completionStatus.bothSynced && (
                    <span className="text-xs ml-1">
                      ({completionStatus.collectionSynced ? 'collection' : 'want list'} synced)
                    </span>
                  )}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                {completionStatus.searchCreated ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
                )}
                <span
                  className={completionStatus.searchCreated ? 'text-green-700 line-through' : ''}
                >
                  Create your first{' '}
                  <Link to="/searches" className="text-primary underline">
                    search
                  </Link>{' '}
                  to find great deals
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
})
