import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useQuery } from '@tanstack/react-query'
import { budgetApi } from '@/lib/api'
import { AlertTriangle, DollarSign, Calendar } from 'lucide-react'
import { useState } from 'react'
import { BudgetDialog } from './BudgetDialog'

export function BudgetWidget() {
  const [showBudgetDialog, setShowBudgetDialog] = useState(false)

  const { data: budgetSummary, isLoading: summaryLoading } = useQuery({
    queryKey: ['budget-summary'],
    queryFn: budgetApi.getBudgetSummary,
  })

  const { data: alerts } = useQuery({
    queryKey: ['budget-alerts'],
    queryFn: budgetApi.getBudgetAlerts,
  })

  if (summaryLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Search Budget
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-muted rounded w-3/4"></div>
            <div className="h-2 bg-muted rounded"></div>
            <div className="h-4 bg-muted rounded w-1/2"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const hasActiveBudget = budgetSummary?.budget
  const percentageUsed = budgetSummary?.percentage_used || 0
  const remainingBudget = budgetSummary?.remaining_budget || 0
  const spentThisMonth = budgetSummary?.spending_this_month || 0
  const daysRemaining = budgetSummary?.days_remaining || 0


  const getBudgetStatus = (percentage: number) => {
    if (percentage >= 90) return { text: 'Critical', variant: 'destructive' as const }
    if (percentage >= 75) return { text: 'Warning', variant: 'secondary' as const }
    return { text: 'On Track', variant: 'default' as const }
  }

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <DollarSign className="h-4 w-4" />
            Search Budget
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowBudgetDialog(true)}
          >
            {hasActiveBudget ? 'Edit' : 'Set Budget'}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {!hasActiveBudget ? (
            <div className="text-center text-muted-foreground py-4">
              <p className="text-sm">No budget set</p>
              <p className="text-xs">Set a monthly budget to track search spending</p>
            </div>
          ) : (
            <>
              {/* Budget Overview */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">
                    ${spentThisMonth.toFixed(2)} of ${budgetSummary?.budget?.monthly_limit.toFixed(2)}
                  </span>
                  <Badge {...getBudgetStatus(percentageUsed)}>
                    {getBudgetStatus(percentageUsed).text}
                  </Badge>
                </div>
                <Progress
                  value={percentageUsed}
                  className="h-2"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{percentageUsed.toFixed(1)}% used</span>
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {daysRemaining} days left
                  </span>
                </div>
              </div>

              {/* Remaining Budget */}
              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div>
                  <p className="text-sm font-medium">Remaining</p>
                  <p className="text-xs text-muted-foreground">This month</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-green-600">
                    ${remainingBudget.toFixed(2)}
                  </p>
                </div>
              </div>

              {/* Budget Alerts */}
              {alerts && alerts.length > 0 && (
                <div className="space-y-2">
                  {alerts.slice(0, 2).map((alert, index) => (
                    <div
                      key={index}
                      className={`flex items-start gap-2 p-2 rounded-lg text-xs ${
                        alert.severity === 'high'
                          ? 'bg-red-50 text-red-700 border border-red-200'
                          : alert.severity === 'medium'
                          ? 'bg-yellow-50 text-yellow-700 border border-yellow-200'
                          : 'bg-blue-50 text-blue-700 border border-blue-200'
                      }`}
                    >
                      <AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                      <span>{alert.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <BudgetDialog
        open={showBudgetDialog}
        onOpenChange={setShowBudgetDialog}
        existingBudget={budgetSummary?.budget}
      />
    </>
  )
}
