import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { SearchChain, SavedSearch } from '@/types/api'
import {
  ArrowRight,
  Search,
  Settings,
  Clock,
  Activity,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface ChainVisualizationProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  chain: SearchChain
  availableSearches: SavedSearch[]
}

export function ChainVisualization({ open, onOpenChange, chain, availableSearches }: ChainVisualizationProps) {
  const linkedSearches = chain.links.map(link => ({
    link,
    search: availableSearches.find(search => search.id === link.search_id)
  })).sort((a, b) => a.link.order_index - b.link.order_index)

  const getConditionDescription = (condition: { condition_type?: string; min_results?: number } | undefined) => {
    switch (condition?.condition_type) {
      case 'results_found':
        return 'When results are found'
      case 'no_results':
        return 'When no results found'
      case 'min_results':
        return `When ≥${condition.min_results} results found`
      default:
        return 'When triggered'
    }
  }

  const getConditionIcon = (condition: { condition_type?: string; min_results?: number } | undefined) => {
    switch (condition?.condition_type) {
      case 'results_found':
        return <CheckCircle className="h-3 w-3 text-green-500" />
      case 'no_results':
        return <XCircle className="h-3 w-3 text-red-500" />
      case 'min_results':
        return <AlertCircle className="h-3 w-3 text-yellow-500" />
      default:
        return <Activity className="h-3 w-3 text-blue-500" />
    }
  }

  const getSearchStatus = (search: SavedSearch | undefined) => {
    if (!search) return { status: 'Unknown', variant: 'secondary' as const }

    return {
      status: search.is_active ? 'Active' : 'Inactive',
      variant: (search.is_active ? 'default' : 'secondary') as const
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Chain Flow: {chain.name}
          </DialogTitle>
          <DialogDescription>
            Visual representation of how this search chain executes
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Chain Overview */}
          <Card>
            <CardContent className="pt-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant={chain.is_active ? 'default' : 'secondary'}>
                    {chain.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {chain.links.length} link{chain.links.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  Created {formatDistanceToNow(new Date(chain.created_at), { addSuffix: true })}
                </div>
              </div>

              {chain.description && (
                <p className="text-sm text-muted-foreground">{chain.description}</p>
              )}
            </CardContent>
          </Card>

          {/* Chain Flow Visualization */}
          {linkedSearches.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Activity className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No links configured</h3>
                <p className="text-muted-foreground text-center">
                  This chain doesn't have any links set up yet.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Execution Flow</h3>

              <div className="space-y-6">
                {linkedSearches.map(({ link, search }, index) => (
                  <div key={link.id} className="space-y-3">
                    {/* Link Card */}
                    <Card className="border-l-4 border-l-blue-500">
                      <CardContent className="pt-4">
                        <div className="space-y-4">
                          {/* Step Header */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline">Step {index + 1}</Badge>
                              <span className="font-medium">
                                {search?.name || 'Unknown Search'}
                              </span>
                              <Badge {...getSearchStatus(search)}>
                                {getSearchStatus(search).status}
                              </Badge>
                            </div>
                            <Search className="h-4 w-4 text-muted-foreground" />
                          </div>

                          {/* Search Details */}
                          {search && (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                              <div>
                                <span className="text-muted-foreground">Platform:</span>
                                <div className="font-medium capitalize">{search.platform}</div>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Query:</span>
                                <div className="font-medium line-clamp-1">{search.query}</div>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Interval:</span>
                                <div className="font-medium">{search.check_interval_hours}h</div>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Last Run:</span>
                                <div className="font-medium">
                                  {search.last_run_at
                                    ? formatDistanceToNow(new Date(search.last_run_at), { addSuffix: true })
                                    : 'Never'
                                  }
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Trigger Condition */}
                          <div className="bg-muted/50 rounded-lg p-3">
                            <div className="flex items-center gap-2 text-sm">
                              {getConditionIcon(link.trigger_condition)}
                              <span className="font-medium">Trigger Condition:</span>
                              <span className="text-muted-foreground">
                                {getConditionDescription(link.trigger_condition)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Arrow to next step */}
                    {index < linkedSearches.length - 1 && (
                      <div className="flex justify-center py-2">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <div className="h-px bg-border flex-1 w-8"></div>
                          <ArrowRight className="h-5 w-5" />
                          <div className="h-px bg-border flex-1 w-8"></div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Chain Execution Notes */}
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="pt-4">
              <div className="flex items-start gap-2">
                <Settings className="h-4 w-4 text-blue-600 mt-0.5" />
                <div className="space-y-2 text-sm">
                  <p className="font-medium text-blue-900">How this chain works:</p>
                  <ul className="space-y-1 text-blue-700">
                    <li>• Chains evaluate automatically when any linked search completes</li>
                    <li>• Each step only triggers if the previous step's condition is met</li>
                    <li>• Inactive searches in the chain will be skipped</li>
                    <li>• You can manually trigger evaluation using the "Evaluate Now" action</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  )
}
