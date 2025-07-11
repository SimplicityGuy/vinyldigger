import { memo, useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { AlertCircle, Package, Heart, RefreshCw, Check, Loader2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { collectionApi, oauthApi, searchApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Link } from 'react-router-dom'

export const DashboardPage = memo(function DashboardPage() {
  const { toast } = useToast()
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncType, setSyncType] = useState<'both' | 'collection' | 'wantlist' | null>(null)

  const { data: collectionStatus } = useQuery({
    queryKey: ['collection-status'],
    queryFn: collectionApi.getCollectionStatus,
    refetchInterval: isSyncing ? 2000 : false, // Poll every 2 seconds while syncing
  })

  const { data: wantListStatus } = useQuery({
    queryKey: ['wantlist-status'],
    queryFn: collectionApi.getWantListStatus,
    refetchInterval: isSyncing ? 2000 : false, // Poll every 2 seconds while syncing
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
  const completionStatus = {
    discogsConnected: discogsOAuthStatus?.is_authorized || false,
    collectionSynced: (collectionStatus?.item_count || 0) > 0 || (wantListStatus?.item_count || 0) > 0,
    searchCreated: searches.length > 0,
  }

  const allTasksCompleted =
    completionStatus.discogsConnected &&
    completionStatus.collectionSynced &&
    completionStatus.searchCreated

  const syncAllMutation = useMutation({
    mutationFn: collectionApi.syncCollection,
    onMutate: () => {
      setIsSyncing(true)
      setSyncType('both')
    },
    onSuccess: () => {
      toast({
        title: 'Sync started',
        description: 'Your collection and want list are being synced with Discogs.',
      })
      // Stop syncing indicator after 30 seconds (typical sync time)
      setTimeout(() => {
        setIsSyncing(false)
        setSyncType(null)
      }, 30000)
    },
    onError: () => {
      setIsSyncing(false)
      setSyncType(null)
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
    },
    onSuccess: () => {
      toast({
        title: 'Sync started',
        description: 'Your collection is being synced with Discogs.',
      })
      setTimeout(() => {
        setIsSyncing(false)
        setSyncType(null)
      }, 20000)
    },
    onError: () => {
      setIsSyncing(false)
      setSyncType(null)
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
    },
    onSuccess: () => {
      toast({
        title: 'Sync started',
        description: 'Your want list is being synced with Discogs.',
      })
      setTimeout(() => {
        setIsSyncing(false)
        setSyncType(null)
      }, 20000)
    },
    onError: () => {
      setIsSyncing(false)
      setSyncType(null)
      toast({
        title: 'Sync failed',
        description: 'Failed to start want list sync.',
        variant: 'destructive',
      })
    },
  })

  // Stop syncing when we detect new items in collection/wantlist
  useEffect(() => {
    if (isSyncing && (collectionStatus?.last_sync_at || wantListStatus?.last_sync_at)) {
      const lastSync = Math.max(
        collectionStatus?.last_sync_at ? new Date(collectionStatus.last_sync_at).getTime() : 0,
        wantListStatus?.last_sync_at ? new Date(wantListStatus.last_sync_at).getTime() : 0
      )
      // If last sync was within the last minute, stop the syncing indicator
      if (lastSync > Date.now() - 60000) {
        setIsSyncing(false)
      }
    }
  }, [isSyncing, collectionStatus?.last_sync_at, wantListStatus?.last_sync_at])

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
                Syncing {syncType === 'collection' ? 'collection' : syncType === 'wantlist' ? 'want list' : 'collection and want list'} with Discogs...
              </p>
              <p className="text-sm text-blue-700">
                This may take a few minutes depending on the size
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Collection</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{collectionStatus?.item_count || 0}</div>
            <p className="text-xs text-muted-foreground">Records in your collection</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Want List</CardTitle>
            <Heart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{wantListStatus?.item_count || 0}</div>
            <p className="text-xs text-muted-foreground">Records on your want list</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Last Sync</CardTitle>
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {collectionStatus?.last_sync_at
                ? new Date(collectionStatus.last_sync_at).toLocaleDateString()
                : 'Never'}
            </div>
            <p className="text-xs text-muted-foreground">Synced with Discogs</p>
          </CardContent>
        </Card>
      </div>

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
                  <RefreshCw className={`h-4 w-4 ${(syncAllMutation.isPending || (isSyncing && syncType === 'both')) ? 'animate-spin' : ''}`} />
                  {(syncAllMutation.isPending || (isSyncing && syncType === 'both')) ? 'Syncing...' : 'Sync All'}
                </Button>
                <Button
                  onClick={() => syncCollectionMutation.mutate()}
                  disabled={syncCollectionMutation.isPending || isSyncing}
                  variant="outline"
                  className="gap-2"
                >
                  <Package className={`h-4 w-4 ${(syncCollectionMutation.isPending || (isSyncing && syncType === 'collection')) ? 'animate-spin' : ''}`} />
                  {(syncCollectionMutation.isPending || (isSyncing && syncType === 'collection')) ? 'Syncing...' : 'Sync Collection Only'}
                </Button>
                <Button
                  onClick={() => syncWantListMutation.mutate()}
                  disabled={syncWantListMutation.isPending || isSyncing}
                  variant="outline"
                  className="gap-2"
                >
                  <Heart className={`h-4 w-4 ${(syncWantListMutation.isPending || (isSyncing && syncType === 'wantlist')) ? 'animate-spin' : ''}`} />
                  {(syncWantListMutation.isPending || (isSyncing && syncType === 'wantlist')) ? 'Syncing...' : 'Sync Want List Only'}
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
                <span className={completionStatus.discogsConnected ? 'text-green-700 line-through' : ''}>
                  Connect your Discogs account in{' '}
                  <Link to="/settings" className="text-primary underline">
                    Settings
                  </Link>
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                {completionStatus.collectionSynced ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
                )}
                <span className={completionStatus.collectionSynced ? 'text-green-700 line-through' : ''}>
                  Sync your collection and want list using the button above
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                {completionStatus.searchCreated ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
                )}
                <span className={completionStatus.searchCreated ? 'text-green-700 line-through' : ''}>
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
