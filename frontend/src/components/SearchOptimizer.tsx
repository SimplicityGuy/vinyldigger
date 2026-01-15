import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { searchApi } from '@/lib/api'
import { SavedSearch } from '@/types/api'
import { useToast } from '@/hooks/useToast'
import {
  Brain,
  Clock,
  TrendingUp,
  Zap,
  Target,
  CheckCircle,
  AlertCircle,
  Loader2
} from 'lucide-react'

interface SearchOptimizerProps {
  search: SavedSearch
}

export function SearchOptimizer({ search }: SearchOptimizerProps) {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [isOptimizing, setIsOptimizing] = useState(false)

  const { data: scheduleSuggestion, isLoading: suggestionLoading } = useQuery({
    queryKey: ['schedule-suggestion', search.id],
    queryFn: () => searchApi.getScheduleSuggestion(search.id),
    enabled: !!search.id,
  })

  const updateOrchestrationMutation = useMutation({
    mutationFn: (data: { optimal_run_times?: number[] }) => searchApi.updateSearchOrchestration(search.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['searches'] })
      queryClient.invalidateQueries({ queryKey: ['schedule-suggestion', search.id] })
      toast({ title: 'Search optimization applied successfully' })
      setIsOptimizing(false)
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to apply optimization',
        description: error.message,
        variant: 'destructive',
      })
      setIsOptimizing(false)
    },
  })

  const applyOptimization = async () => {
    if (!scheduleSuggestion) return

    setIsOptimizing(true)

    try {
      // Apply the suggested optimal run times
      await updateOrchestrationMutation.mutateAsync({
        optimal_run_times: scheduleSuggestion.suggested_times,
      })
    } catch {
      // Error handling is done in the mutation
    }
  }

  const getOptimizationScore = () => {
    if (!scheduleSuggestion) return 0

    // Simple scoring based on improvement potential
    const improvementText = scheduleSuggestion.estimated_improvement.toLowerCase()
    if (improvementText.includes('significant')) return 85
    if (improvementText.includes('moderate')) return 65
    if (improvementText.includes('minor')) return 40
    return 20
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }


  const formatTimeSlot = (hour: number) => {
    const time = new Date()
    time.setHours(hour, 0, 0, 0)
    return time.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })
  }

  const optimizationScore = getOptimizationScore()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="text-lg flex items-center gap-2">
          <Brain className="h-5 w-5" />
          AI Search Optimizer
        </CardTitle>
        <Badge variant="outline" className="flex items-center gap-1">
          <Zap className="h-3 w-3" />
          ML-Powered
        </Badge>
      </CardHeader>
      <CardContent className="space-y-6">
        {suggestionLoading ? (
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-muted rounded w-3/4"></div>
            <div className="h-2 bg-muted rounded"></div>
            <div className="h-4 bg-muted rounded w-1/2"></div>
          </div>
        ) : !scheduleSuggestion ? (
          <div className="text-center text-muted-foreground py-8">
            <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-sm">No optimization data available</p>
            <p className="text-xs">Run this search a few times to generate suggestions</p>
          </div>
        ) : (
          <>
            {/* Optimization Score */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Optimization Score</span>
                <span className={`text-lg font-bold ${getScoreColor(optimizationScore)}`}>
                  {optimizationScore}/100
                </span>
              </div>
              <Progress
                value={optimizationScore}
                className="h-2"
              />
              <p className="text-xs text-muted-foreground">
                Based on current performance and improvement potential
              </p>
            </div>

            {/* Current vs Suggested Schedule */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <h4 className="text-sm font-medium flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Current Schedule
                </h4>
                <div className="bg-muted/50 rounded-lg p-3">
                  <p className="text-sm">{scheduleSuggestion.current_schedule}</p>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-sm font-medium flex items-center gap-1">
                  <Target className="h-3 w-3" />
                  Suggested Times
                </h4>
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <div className="flex flex-wrap gap-1">
                    {scheduleSuggestion.suggested_times.map((hour, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {formatTimeSlot(hour)}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* AI Reasoning */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium flex items-center gap-1">
                <Brain className="h-3 w-3" />
                AI Analysis
              </h4>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-sm text-blue-800">{scheduleSuggestion.reasoning}</p>
              </div>
            </div>

            {/* Expected Improvement */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                Expected Improvement
              </h4>
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-start gap-2">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-green-800">{scheduleSuggestion.estimated_improvement}</p>
              </div>
            </div>

            {/* Optimization Features */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium">Optimization Features</h4>
              <div className="grid grid-cols-1 gap-2">
                <div className="flex items-center gap-2 text-xs">
                  <CheckCircle className="h-3 w-3 text-green-500" />
                  <span>Peak marketplace activity detection</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <CheckCircle className="h-3 w-3 text-green-500" />
                  <span>Historical performance analysis</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <CheckCircle className="h-3 w-3 text-green-500" />
                  <span>Competition pattern recognition</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <AlertCircle className="h-3 w-3 text-yellow-500" />
                  <span>Seller listing behavior prediction</span>
                </div>
              </div>
            </div>

            {/* Apply Optimization */}
            <div className="pt-4 border-t">
              <Button
                onClick={applyOptimization}
                disabled={isOptimizing || updateOrchestrationMutation.isPending}
                className="w-full"
              >
                {(isOptimizing || updateOrchestrationMutation.isPending) && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                <Zap className="mr-2 h-4 w-4" />
                Apply AI Optimization
              </Button>
              <p className="text-xs text-muted-foreground text-center mt-2">
                This will update your search schedule to the optimal times
              </p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
