import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useQuery } from '@tanstack/react-query'
import { budgetApi } from '@/lib/api'
import { TrendingUp, TrendingDown, Minus, Calendar } from 'lucide-react'
import { useState } from 'react'

const PERIOD_OPTIONS = [
  { label: '7 Days', value: 7 },
  { label: '30 Days', value: 30 },
  { label: '90 Days', value: 90 },
]

export function SpendingChart() {
  const [selectedPeriod, setSelectedPeriod] = useState(30)

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['spending-analytics', selectedPeriod],
    queryFn: () => budgetApi.getSpendingAnalytics(selectedPeriod),
  })

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Spending Analytics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-4">
            <div className="flex gap-2">
              {PERIOD_OPTIONS.map((_, i) => (
                <div key={i} className="h-8 bg-muted rounded w-16"></div>
              ))}
            </div>
            <div className="space-y-3">
              <div className="h-4 bg-muted rounded w-3/4"></div>
              <div className="h-8 bg-muted rounded"></div>
              <div className="h-4 bg-muted rounded w-1/2"></div>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'over_budget':
        return <TrendingUp className="h-4 w-4 text-red-500" />
      case 'under_budget':
        return <TrendingDown className="h-4 w-4 text-green-500" />
      default:
        return <Minus className="h-4 w-4 text-yellow-500" />
    }
  }

  const getTrendBadge = (trend: string) => {
    switch (trend) {
      case 'over_budget':
        return { text: 'Over Budget', variant: 'destructive' as const }
      case 'under_budget':
        return { text: 'Under Budget', variant: 'default' as const }
      default:
        return { text: 'On Track', variant: 'secondary' as const }
    }
  }

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'over_budget':
        return 'text-red-600'
      case 'under_budget':
        return 'text-green-600'
      default:
        return 'text-yellow-600'
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Spending Analytics
        </CardTitle>
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map((option) => (
            <Button
              key={option.value}
              variant={selectedPeriod === option.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedPeriod(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {!analytics ? (
          <div className="text-center text-muted-foreground py-8">
            <p className="text-sm">No spending data available</p>
            <p className="text-xs">Start running searches to see analytics</p>
          </div>
        ) : (
          <>
            {/* Overview Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Total Spent</p>
                <p className="text-2xl font-bold">${analytics.total_spent.toFixed(2)}</p>
                <div className="flex items-center gap-2">
                  {getTrendIcon(analytics.trend)}
                  <Badge {...getTrendBadge(analytics.trend)}>
                    {getTrendBadge(analytics.trend).text}
                  </Badge>
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Daily Average</p>
                <p className="text-2xl font-bold">${analytics.average_daily.toFixed(2)}</p>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  Last {analytics.days_elapsed} days
                </p>
              </div>
            </div>

            {/* Budget Comparison */}
            {analytics.budget_limit > 0 && (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Budget Progress</span>
                  <span className="text-sm text-muted-foreground">
                    ${analytics.total_spent.toFixed(2)} / ${analytics.budget_limit.toFixed(2)}
                  </span>
                </div>

                {/* Simple Progress Bar */}
                <div className="w-full bg-muted rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${
                      analytics.total_spent > analytics.budget_limit
                        ? 'bg-red-500'
                        : analytics.total_spent > analytics.budget_limit * 0.75
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                    }`}
                    style={{
                      width: `${Math.min((analytics.total_spent / analytics.budget_limit) * 100, 100)}%`
                    }}
                  />
                </div>

                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>
                    {((analytics.total_spent / analytics.budget_limit) * 100).toFixed(1)}% used
                  </span>
                  <span>{analytics.days_remaining} days remaining</span>
                </div>
              </div>
            )}

            {/* Projection */}
            <div className="bg-muted/50 rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Projected Monthly Spend</span>
                <span className={`text-lg font-bold ${getTrendColor(analytics.trend)}`}>
                  ${analytics.projection.toFixed(2)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Based on current spending patterns over {selectedPeriod} days
              </p>
              {analytics.budget_limit > 0 && analytics.projection > analytics.budget_limit && (
                <p className="text-xs text-red-600 font-medium">
                  ⚠️ Projected to exceed budget by ${(analytics.projection - analytics.budget_limit).toFixed(2)}
                </p>
              )}
            </div>

            {/* Period Summary */}
            <div className="text-xs text-muted-foreground space-y-1">
              <p>• Analysis period: {analytics.days_elapsed} days</p>
              <p>• Days remaining in budget period: {analytics.days_remaining}</p>
              <p>• Trend: {analytics.trend.replace('_', ' ')}</p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
