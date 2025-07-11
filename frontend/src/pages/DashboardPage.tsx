import { memo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Package, Heart, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { collectionApi, oauthApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Link } from 'react-router-dom'

export const DashboardPage = memo(function DashboardPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: collectionStatus } = useQuery({
    queryKey: ['collection-status'],
    queryFn: collectionApi.getCollectionStatus,
  })

  const { data: wantListStatus } = useQuery({
    queryKey: ['wantlist-status'],
    queryFn: collectionApi.getWantListStatus,
  })

  const { data: discogsOAuthStatus } = useQuery({
    queryKey: ['oauth-status', 'discogs'],
    queryFn: () => oauthApi.getOAuthStatus('discogs'),
  })

  const syncMutation = useMutation({
    mutationFn: collectionApi.syncCollection,
    onSuccess: () => {
      toast({
        title: 'Sync started',
        description: 'Your collection is being synced with Discogs.',
      })
      // Invalidate queries after a delay to allow sync to progress
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['collection-status'] })
        queryClient.invalidateQueries({ queryKey: ['wantlist-status'] })
      }, 5000)
    },
    onError: () => {
      toast({
        title: 'Sync failed',
        description: 'Failed to start collection sync.',
        variant: 'destructive',
      })
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Overview of your vinyl collection and recent activity
        </p>
      </div>

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
        <CardContent className="flex gap-4">
          {discogsOAuthStatus?.is_authorized ? (
            <Button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
              {syncMutation.isPending ? 'Syncing...' : 'Sync Collection'}
            </Button>
          ) : (
            <div className="flex items-center gap-4">
              <Button disabled className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Sync Collection
              </Button>
              <p className="text-sm text-muted-foreground">
                Connect your Discogs account in{' '}
                <Link to="/settings" className="text-primary underline">
                  Settings
                </Link>{' '}
                to sync your collection.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Setup Notice */}
      {(!collectionStatus?.item_count || collectionStatus.item_count === 0) && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader className="flex flex-row items-center gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <CardTitle className="text-lg">Get Started</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              To start using VinylDigger, make sure to:
            </p>
            <ol className="mt-2 list-inside list-decimal space-y-1 text-sm">
              <li>Connect your Discogs account in Settings</li>
              <li>Sync your collection using the button above</li>
              <li>Create your first search to find great deals</li>
            </ol>
          </CardContent>
        </Card>
      )}
    </div>
  )
})
