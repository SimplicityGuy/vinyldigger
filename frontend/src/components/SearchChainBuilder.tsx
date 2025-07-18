import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { chainApi, searchApi } from '@/lib/api'
import { Plus, Link, Play, Pause } from 'lucide-react'
import { ChainCard } from './ChainCard'
import { ChainDialog } from './ChainDialog'

export function SearchChainBuilder() {
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const { data: chains, isLoading: chainsLoading } = useQuery({
    queryKey: ['chains'],
    queryFn: chainApi.getChains,
  })

  const { data: searches } = useQuery({
    queryKey: ['searches'],
    queryFn: searchApi.getSearches,
  })

  const activeChains = chains?.filter(chain => chain.is_active) || []
  const inactiveChains = chains?.filter(chain => !chain.is_active) || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Search Chains</h2>
          <p className="text-muted-foreground">
            Create automated workflows that trigger searches based on results from other searches
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)} className="sm:w-auto">
          <Plus className="mr-2 h-4 w-4" />
          Create Chain
        </Button>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="flex items-center p-6">
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-green-100 rounded-full">
                <Play className="h-4 w-4 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{activeChains.length}</p>
                <p className="text-xs text-muted-foreground">Active Chains</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center p-6">
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-gray-100 rounded-full">
                <Pause className="h-4 w-4 text-gray-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{inactiveChains.length}</p>
                <p className="text-xs text-muted-foreground">Inactive Chains</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center p-6">
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-blue-100 rounded-full">
                <Link className="h-4 w-4 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {chains?.reduce((acc, chain) => acc + chain.links.length, 0) || 0}
                </p>
                <p className="text-xs text-muted-foreground">Total Links</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chains List */}
      {chainsLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-muted rounded w-3/4"></div>
                  <div className="h-3 bg-muted rounded w-1/2"></div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="animate-pulse space-y-3">
                  <div className="h-3 bg-muted rounded"></div>
                  <div className="h-3 bg-muted rounded w-5/6"></div>
                  <div className="flex gap-2">
                    <div className="h-6 bg-muted rounded w-16"></div>
                    <div className="h-6 bg-muted rounded w-12"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : !chains || chains.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Link className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No search chains yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create your first search chain to automate search workflows
            </p>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Chain
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Active Chains */}
          {activeChains.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold">Active Chains</h3>
                <Badge variant="default" className="text-xs">
                  {activeChains.length} running
                </Badge>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {activeChains.map((chain) => (
                  <ChainCard key={chain.id} chain={chain} availableSearches={searches || []} />
                ))}
              </div>
            </div>
          )}

          {/* Inactive Chains */}
          {inactiveChains.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold">Inactive Chains</h3>
                <Badge variant="secondary" className="text-xs">
                  {inactiveChains.length} paused
                </Badge>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {inactiveChains.map((chain) => (
                  <ChainCard key={chain.id} chain={chain} availableSearches={searches || []} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create Chain Dialog */}
      <ChainDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        availableSearches={searches || []}
      />
    </div>
  )
}
