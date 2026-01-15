import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { budgetApi } from '@/lib/api'
import { SavedSearch } from '@/types/api'
import {
  Lightbulb,
  TrendingUp,
  Clock,
  DollarSign,
  Users,
  Target,
  AlertTriangle,
  CheckCircle,
  ArrowRight
} from 'lucide-react'
import { useState } from 'react'

interface IntelligentInsightsProps {
  searches: SavedSearch[]
}

interface Insight {
  id: string
  type: 'optimization' | 'budget' | 'performance' | 'market' | 'automation'
  priority: 'high' | 'medium' | 'low'
  title: string
  description: string
  action?: string
  actionable: boolean
  impact: string
  effort: 'low' | 'medium' | 'high'
}

export function IntelligentInsights({ searches }: IntelligentInsightsProps) {
  const [selectedInsight, setSelectedInsight] = useState<string | null>(null)

  const { data: budgetSummary } = useQuery({
    queryKey: ['budget-summary'],
    queryFn: budgetApi.getBudgetSummary,
  })

  const { data: spendingAnalytics } = useQuery({
    queryKey: ['spending-analytics', 30],
    queryFn: () => budgetApi.getSpendingAnalytics(30),
  })

  // Generate insights based on user data
  const generateInsights = (): Insight[] => {
    const insights: Insight[] = []

    // Budget-related insights
    if (budgetSummary?.percentage_used && budgetSummary.percentage_used > 80) {
      insights.push({
        id: 'budget-critical',
        type: 'budget',
        priority: 'high',
        title: 'Budget Alert: Critical Usage',
        description: `You've used ${budgetSummary.percentage_used.toFixed(1)}% of your monthly budget. Consider optimizing search frequency or increasing your budget.`,
        action: 'Review Budget Settings',
        actionable: true,
        impact: 'Prevent budget overrun',
        effort: 'low'
      })
    }

    // Search optimization insights
    const activeSearches = searches.filter(s => s.is_active)
    const inactiveSearches = searches.filter(s => !s.is_active)

    if (inactiveSearches.length > 0) {
      insights.push({
        id: 'inactive-searches',
        type: 'optimization',
        priority: 'medium',
        title: 'Optimize Search Portfolio',
        description: `You have ${inactiveSearches.length} inactive searches. Consider reactivating valuable searches or removing outdated ones.`,
        action: 'Review Inactive Searches',
        actionable: true,
        impact: 'Improve search coverage',
        effort: 'medium'
      })
    }

    // Frequency optimization
    const highFrequencySearches = activeSearches.filter(s => s.check_interval_hours <= 6)
    if (highFrequencySearches.length > 3) {
      insights.push({
        id: 'frequency-optimization',
        type: 'performance',
        priority: 'medium',
        title: 'High-Frequency Search Alert',
        description: `${highFrequencySearches.length} searches run every 6 hours or less. This may impact your budget significantly.`,
        action: 'Optimize Intervals',
        actionable: true,
        impact: 'Reduce costs by 20-40%',
        effort: 'low'
      })
    }

    // Platform optimization
    const both = activeSearches.filter(s => s.platform === 'both').length

    if (both === 0 && activeSearches.length > 2) {
      insights.push({
        id: 'platform-optimization',
        type: 'market',
        priority: 'medium',
        title: 'Cross-Platform Opportunity',
        description: 'None of your searches cover both platforms. You might be missing deals by limiting to single platforms.',
        action: 'Enable Cross-Platform',
        actionable: true,
        impact: 'Increase deal discovery by 30-50%',
        effort: 'low'
      })
    }

    // Automation opportunity
    if (activeSearches.length >= 3 && !searches.some(s => s.depends_on_search)) {
      insights.push({
        id: 'automation-opportunity',
        type: 'automation',
        priority: 'low',
        title: 'Search Chain Opportunity',
        description: 'With multiple active searches, you could create automated chains to trigger related searches based on results.',
        action: 'Create Search Chains',
        actionable: true,
        impact: 'Automate 60% of manual work',
        effort: 'medium'
      })
    }

    // Performance insights
    const oldSearches = activeSearches.filter(s => {
      const daysSinceLastRun = s.last_run_at
        ? (Date.now() - new Date(s.last_run_at).getTime()) / (1000 * 60 * 60 * 24)
        : 999
      return daysSinceLastRun > 7
    })

    if (oldSearches.length > 0) {
      insights.push({
        id: 'stale-searches',
        type: 'performance',
        priority: 'high',
        title: 'Stale Search Detection',
        description: `${oldSearches.length} searches haven't run in over a week. They may have configuration issues or need attention.`,
        action: 'Review Search Status',
        actionable: true,
        impact: 'Restore search functionality',
        effort: 'medium'
      })
    }

    // Market insights based on spending patterns
    if (spendingAnalytics?.trend === 'under_budget' && spendingAnalytics.budget_limit > 0) {
      const utilizationRate = (spendingAnalytics.total_spent / spendingAnalytics.budget_limit) * 100
      if (utilizationRate < 50) {
        insights.push({
          id: 'budget-underutilized',
          type: 'market',
          priority: 'low',
          title: 'Budget Underutilization',
          description: `You're only using ${utilizationRate.toFixed(0)}% of your budget. Consider increasing search frequency or expanding search scope.`,
          action: 'Increase Search Activity',
          actionable: true,
          impact: 'Find more deals within budget',
          effort: 'low'
        })
      }
    }

    return insights.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 }
      return priorityOrder[b.priority] - priorityOrder[a.priority]
    })
  }

  const insights = generateInsights()

  const getInsightIcon = (type: Insight['type']) => {
    switch (type) {
      case 'optimization': return <TrendingUp className="h-4 w-4" />
      case 'budget': return <DollarSign className="h-4 w-4" />
      case 'performance': return <Clock className="h-4 w-4" />
      case 'market': return <Target className="h-4 w-4" />
      case 'automation': return <Users className="h-4 w-4" />
      default: return <Lightbulb className="h-4 w-4" />
    }
  }

  const getPriorityColor = (priority: Insight['priority']) => {
    switch (priority) {
      case 'high': return 'text-red-600 bg-red-50 border-red-200'
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-200'
    }
  }

  const getPriorityIcon = (priority: Insight['priority']) => {
    switch (priority) {
      case 'high': return <AlertTriangle className="h-3 w-3" />
      case 'medium': return <Clock className="h-3 w-3" />
      case 'low': return <CheckCircle className="h-3 w-3" />
    }
  }

  const getEffortBadge = (effort: Insight['effort']) => {
    const variants = {
      low: { variant: 'default' as const, text: 'Quick Fix' },
      medium: { variant: 'secondary' as const, text: 'Medium Effort' },
      high: { variant: 'outline' as const, text: 'Complex Task' }
    }
    return variants[effort]
  }

  if (insights.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
          <h3 className="text-lg font-semibold mb-2 text-green-700">All Good!</h3>
          <p className="text-muted-foreground text-center">
            Your search setup is optimized. No immediate improvements needed.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5" />
          Intelligent Insights
          <Badge variant="outline" className="text-xs">
            {insights.length} suggestion{insights.length !== 1 ? 's' : ''}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {insights.map((insight) => (
          <Card
            key={insight.id}
            className={`transition-all cursor-pointer ${
              selectedInsight === insight.id
                ? 'ring-2 ring-primary'
                : 'hover:shadow-md'
            }`}
            onClick={() => setSelectedInsight(
              selectedInsight === insight.id ? null : insight.id
            )}
          >
            <CardContent className="pt-4">
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <div className={`p-2 rounded-lg ${getPriorityColor(insight.priority)}`}>
                      {getInsightIcon(insight.type)}
                    </div>
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">{insight.title}</h4>
                        <Badge
                          variant={insight.priority === 'high' ? 'destructive' : 'outline'}
                          className="text-xs flex items-center gap-1"
                        >
                          {getPriorityIcon(insight.priority)}
                          {insight.priority}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {insight.description}
                      </p>
                    </div>
                  </div>
                  <ArrowRight
                    className={`h-4 w-4 text-muted-foreground transition-transform ${
                      selectedInsight === insight.id ? 'rotate-90' : ''
                    }`}
                  />
                </div>

                {/* Expanded Details */}
                {selectedInsight === insight.id && (
                  <div className="pt-3 border-t space-y-3">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Expected Impact:</span>
                        <p className="font-medium text-green-600">{insight.impact}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Effort Required:</span>
                        <div className="mt-1">
                          <Badge {...getEffortBadge(insight.effort)}>
                            {getEffortBadge(insight.effort).text}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    {insight.actionable && insight.action && (
                      <Button variant="outline" size="sm" className="w-full">
                        {insight.action}
                        <ArrowRight className="ml-2 h-3 w-3" />
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}

        {/* Summary Stats */}
        <div className="pt-4 border-t">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-lg font-bold text-red-600">
                {insights.filter(i => i.priority === 'high').length}
              </div>
              <div className="text-xs text-muted-foreground">High Priority</div>
            </div>
            <div>
              <div className="text-lg font-bold text-yellow-600">
                {insights.filter(i => i.priority === 'medium').length}
              </div>
              <div className="text-xs text-muted-foreground">Medium Priority</div>
            </div>
            <div>
              <div className="text-lg font-bold text-blue-600">
                {insights.filter(i => i.priority === 'low').length}
              </div>
              <div className="text-xs text-muted-foreground">Low Priority</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
