import { useQuery } from '@tanstack/react-query'
import { BudgetWidget } from '@/components/BudgetWidget'
import { SpendingChart } from '@/components/SpendingChart'
import { searchApi } from '@/lib/api'
import { IntelligentInsights } from '@/components/IntelligentInsights'

export function BudgetPage() {
  const { data: searches } = useQuery({
    queryKey: ['searches'],
    queryFn: searchApi.getSearches,
  })

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Budget & Analytics</h1>
        <p className="text-muted-foreground">
          Monitor your search spending and get intelligent insights to optimize performance
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BudgetWidget />
        <SpendingChart />
      </div>

      {searches && (
        <IntelligentInsights searches={searches} />
      )}
    </div>
  )
}
