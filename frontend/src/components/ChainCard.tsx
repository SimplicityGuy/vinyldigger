import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { chainApi } from '@/lib/api'
import { SearchChain, SavedSearch } from '@/types/api'
import { useToast } from '@/hooks/useToast'
import {
  MoreVertical,
  Play,
  Pause,
  Edit,
  Trash2,
  Link,
  ArrowRight,
  Activity
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ChainDialog } from './ChainDialog'
import { ChainVisualization } from './ChainVisualization'

interface ChainCardProps {
  chain: SearchChain
  availableSearches: SavedSearch[]
}

export function ChainCard({ chain, availableSearches }: ChainCardProps) {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [showVisualization, setShowVisualization] = useState(false)

  const toggleChainMutation = useMutation({
    mutationFn: () => chainApi.updateChain(chain.id, { is_active: !chain.is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chains'] })
      toast({
        title: `Chain ${chain.is_active ? 'paused' : 'activated'}`,
        description: `${chain.name} is now ${chain.is_active ? 'inactive' : 'active'}`
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to update chain',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const deleteChainMutation = useMutation({
    mutationFn: () => chainApi.deleteChain(chain.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chains'] })
      toast({ title: 'Chain deleted successfully' })
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to delete chain',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const evaluateChainMutation = useMutation({
    mutationFn: () => chainApi.evaluateChain(chain.id),
    onSuccess: (data) => {
      toast({
        title: 'Chain evaluated',
        description: `${data.count} searches triggered`
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to evaluate chain',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this chain?')) {
      deleteChainMutation.mutate()
    }
  }

  const handleEvaluate = () => {
    evaluateChainMutation.mutate()
  }

  const relativeTime = formatDistanceToNow(new Date(chain.created_at), { addSuffix: true })
  const linkedSearches = chain.links.map(link =>
    availableSearches.find(search => search.id === link.search_id)
  ).filter(Boolean)

  return (
    <>
      <Card className="group hover:shadow-md transition-shadow">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="space-y-1 flex-1">
              <CardTitle className="text-lg leading-6 line-clamp-2 flex items-center gap-2">
                {chain.name}
                <Badge variant={chain.is_active ? 'default' : 'secondary'} className="text-xs">
                  {chain.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </CardTitle>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Link className="h-3 w-3" />
                <span>{chain.links.length} link{chain.links.length !== 1 ? 's' : ''}</span>
                <span>•</span>
                <span>{relativeTime}</span>
              </div>
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setShowVisualization(true)}>
                  <Activity className="mr-2 h-4 w-4" />
                  View Flow
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={handleEvaluate}
                  disabled={evaluateChainMutation.isPending || !chain.is_active}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Evaluate Now
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setShowEditDialog(true)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => toggleChainMutation.mutate()}
                  disabled={toggleChainMutation.isPending}
                >
                  {chain.is_active ? (
                    <>
                      <Pause className="mr-2 h-4 w-4" />
                      Pause
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Activate
                    </>
                  )}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleDelete}
                  className="text-red-600 focus:text-red-600"
                  disabled={deleteChainMutation.isPending}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Description */}
          {chain.description && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {chain.description}
            </p>
          )}

          {/* Chain Flow Preview */}
          {chain.links.length > 0 ? (
            <div className="space-y-3">
              <div className="text-xs font-medium text-muted-foreground">Chain Flow:</div>
              <div className="bg-muted/50 rounded-lg p-3">
                <div className="flex flex-wrap items-center gap-2">
                  {chain.links
                    .sort((a, b) => a.order_index - b.order_index)
                    .map((link, index) => {
                      const search = linkedSearches.find(s => s?.id === link.search_id)
                      return (
                        <div key={link.id} className="flex items-center gap-2">
                          <div className="flex items-center gap-1">
                            <Badge variant="outline" className="text-xs">
                              {search?.name || 'Unknown Search'}
                            </Badge>
                          </div>
                          {index < chain.links.length - 1 && (
                            <ArrowRight className="h-3 w-3 text-muted-foreground" />
                          )}
                        </div>
                      )
                    })}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-muted/50 rounded-lg p-3 text-center">
              <p className="text-sm text-muted-foreground">No links configured</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowVisualization(true)}
              className="flex-1"
            >
              <Activity className="mr-2 h-3 w-3" />
              View Flow
            </Button>
            <Button
              variant={chain.is_active ? 'secondary' : 'default'}
              size="sm"
              onClick={() => toggleChainMutation.mutate()}
              disabled={toggleChainMutation.isPending}
              className="flex-1"
            >
              {chain.is_active ? (
                <>
                  <Pause className="mr-2 h-3 w-3" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="mr-2 h-3 w-3" />
                  Activate
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Dialogs */}
      <ChainDialog
        open={showEditDialog}
        onOpenChange={setShowEditDialog}
        chain={chain}
        availableSearches={availableSearches}
      />

      <ChainVisualization
        open={showVisualization}
        onOpenChange={setShowVisualization}
        chain={chain}
        availableSearches={availableSearches}
      />
    </>
  )
}
