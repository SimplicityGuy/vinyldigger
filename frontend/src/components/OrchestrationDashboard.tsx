import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { budgetApi, chainApi, templateApi, searchApi } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'
import {
  Activity,
  DollarSign,
  Link2,
  FileText,
  TrendingUp,
  Clock,
  AlertCircle,
  CheckCircle,
  XCircle,
  Loader2,
  BarChart3,
  Zap,
  Target,
  Calendar,
} from 'lucide-react'

export function OrchestrationDashboard() {
  const [selectedTab, setSelectedTab] = useState('overview')

  // Fetch all orchestration data
  const { data: budgetUsage } = useQuery({
    queryKey: ['budget-usage'],
    queryFn: budgetApi.getBudgetUsage,
  })

  const { data: chains } = useQuery({
    queryKey: ['chains'],
    queryFn: chainApi.getChains,
  })

  const { data: templates } = useQuery({
    queryKey: ['templates'],
    queryFn: () => templateApi.getTemplates(),
  })

  // Template analytics are calculated in the templates tab
  // No need to fetch separately

  const { data: searches } = useQuery({
    queryKey: ['searches'],
    queryFn: searchApi.getSearches,
  })

  // Calculate orchestration statistics
  const orchestrationStats = {
    activeChains: chains?.filter(c => c.is_active).length || 0,
    totalTemplates: templates?.length || 0,
    publicTemplates: templates?.filter(t => t.is_public).length || 0,
    budgetUtilization: budgetUsage?.percentage_used || 0,
    scheduledSearches: searches?.filter(s => s.is_active).length || 0,
    dependentSearches: searches?.filter(s => s.depends_on_search).length || 0,
  }

  // Get recent search executions
  const recentSearches = searches
    ?.filter(s => s.last_run_at)
    .sort((a, b) => new Date(b.last_run_at!).getTime() - new Date(a.last_run_at!).getTime())
    .slice(0, 5) || []

  // Get active chains with status
  const activeChainsWithStatus = chains
    ?.filter(c => c.is_active)
    .map(chain => {
      const chainSearches = searches?.filter(s => s.chain_id === chain.id) || []
      const completedSearches = chainSearches.filter(s => s.status === 'completed').length
      const totalSearches = chainSearches.length
      const progress = totalSearches > 0 ? (completedSearches / totalSearches) * 100 : 0

      return {
        ...chain,
        progress,
        totalSearches,
        completedSearches,
      }
    }) || []

  // Get most used templates
  const popularTemplates = templates
    ?.sort((a, b) => b.usage_count - a.usage_count)
    .slice(0, 5) || []

  const getStatusIcon = (status: string | null) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'running':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      case 'budget_exceeded':
        return <AlertCircle className="h-4 w-4 text-orange-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string | null) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>
      case 'running':
        return <Badge variant="default">Running</Badge>
      case 'budget_exceeded':
        return <Badge variant="warning">Budget Exceeded</Badge>
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>
      default:
        return <Badge variant="secondary">Pending</Badge>
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold">Orchestration Dashboard</h2>
        <p className="text-muted-foreground">
          Monitor and manage your automated search orchestration
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Budget Utilization</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{orchestrationStats.budgetUtilization.toFixed(1)}%</div>
            <Progress value={orchestrationStats.budgetUtilization} className="mt-2" />
            <p className="text-xs text-muted-foreground mt-2">
              ${budgetUsage?.budget?.current_spent.toFixed(2)} of ${budgetUsage?.budget?.monthly_limit.toFixed(2)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Chains</CardTitle>
            <Link2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{orchestrationStats.activeChains}</div>
            <p className="text-xs text-muted-foreground mt-2">
              Running automated workflows
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{orchestrationStats.totalTemplates}</div>
            <p className="text-xs text-muted-foreground mt-2">
              {orchestrationStats.publicTemplates} public templates
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Scheduled Searches</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{orchestrationStats.scheduledSearches}</div>
            <p className="text-xs text-muted-foreground mt-2">
              {orchestrationStats.dependentSearches} with dependencies
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="chains">Chains</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="schedule">Schedule</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Recent Executions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Recent Executions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recentSearches.length > 0 ? (
                    recentSearches.map((search) => (
                      <div key={search.id} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(search.status || null)}
                          <div>
                            <p className="text-sm font-medium">{search.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {search.last_run_at ? formatDistanceToNow(new Date(search.last_run_at), { addSuffix: true }) : 'Never'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {search.results_count} results
                          </Badge>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No recent executions
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Popular Templates */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Popular Templates
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {popularTemplates.length > 0 ? (
                    popularTemplates.map((template) => (
                      <div key={template.id} className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium">{template.name}</p>
                          <p className="text-xs text-muted-foreground">{template.category}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            {template.usage_count} uses
                          </Badge>
                          {template.is_public && (
                            <Badge variant="outline" className="text-xs">
                              Public
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No templates created yet
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Budget Alert */}
          {budgetUsage && budgetUsage.percentage_used && budgetUsage.percentage_used > 80 && (
            <Card className="border-orange-200 bg-orange-50">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-orange-700">
                  <AlertCircle className="h-5 w-5" />
                  Budget Alert
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-orange-600">
                  You've used {budgetUsage.percentage_used?.toFixed(1)}% of your monthly budget.
                  Consider adjusting your search frequency or budget limit to avoid interruptions.
                </p>
                <div className="mt-3 flex gap-2">
                  <Button size="sm" variant="outline">
                    View Budget Settings
                  </Button>
                  <Button size="sm" variant="outline">
                    Optimize Searches
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="chains" className="space-y-4">
          {/* Active Chains */}
          <Card>
            <CardHeader>
              <CardTitle>Active Search Chains</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {activeChainsWithStatus.length > 0 ? (
                  activeChainsWithStatus.map((chain) => (
                    <div key={chain.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{chain.name}</p>
                          <p className="text-sm text-muted-foreground">{chain.description}</p>
                        </div>
                        <Badge variant="outline">
                          {chain.completedSearches}/{chain.totalSearches} searches
                        </Badge>
                      </div>
                      <Progress value={chain.progress} className="h-2" />
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No active chains. Create a chain to automate your search workflow.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="templates" className="space-y-4">
          {/* Template Analytics */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Uses</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {templates?.reduce((sum, t) => sum + t.usage_count, 0) || 0}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Across all templates
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Uses/Template</CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {templates && templates.length > 0
                    ? (templates.reduce((sum, t) => sum + t.usage_count, 0) / templates.length).toFixed(1)
                    : '0'}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Template effectiveness
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Categories</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {new Set(templates?.map(t => t.category)).size || 0}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Template diversity
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Template List */}
          <Card>
            <CardHeader>
              <CardTitle>Template Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {templates && templates.length > 0 ? (
                  templates
                    .sort((a, b) => b.usage_count - a.usage_count)
                    .map((template) => (
                      <div key={template.id} className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="font-medium">{template.name}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="secondary" className="text-xs">
                              {template.category}
                            </Badge>
                            {template.is_public && (
                              <Badge variant="outline" className="text-xs">
                                Public
                              </Badge>
                            )}
                            <span className="text-xs text-muted-foreground">
                              {Object.keys(template.parameters).length} parameters
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium">{template.usage_count} uses</p>
                          <p className="text-xs text-muted-foreground">
                            Created {formatDistanceToNow(new Date(template.created_at), { addSuffix: true })}
                          </p>
                        </div>
                      </div>
                    ))
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No templates created yet
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="schedule" className="space-y-4">
          {/* Scheduled Searches */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Search Schedule
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {searches && searches.filter(s => s.is_active).length > 0 ? (
                  searches
                    .filter(s => s.is_active)
                    .sort((a, b) => a.check_interval_hours - b.check_interval_hours)
                    .map((search) => (
                      <div key={search.id} className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{search.name}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              Every {search.check_interval_hours}h
                            </Badge>
                            {search.optimal_run_times.length > 0 && (
                              <span className="text-xs text-muted-foreground">
                                Preferred: {search.optimal_run_times.map(h => `${h}:00`).join(', ')}
                              </span>
                            )}
                            {search.depends_on_search && (
                              <Badge variant="secondary" className="text-xs">
                                Dependent
                              </Badge>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          {search.last_run_at ? (
                            <>
                              <p className="text-sm">{getStatusBadge(search.status || null)}</p>
                              <p className="text-xs text-muted-foreground mt-1">
                                Last run {search.last_run_at ? formatDistanceToNow(new Date(search.last_run_at), { addSuffix: true }) : 'Never'}
                              </p>
                            </>
                          ) : (
                            <p className="text-sm text-muted-foreground">Never run</p>
                          )}
                        </div>
                      </div>
                    ))
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No active searches scheduled
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Schedule Optimization Suggestions */}
          {searches && searches.some(s => s.priority_level && s.priority_level < 5) && (
            <Card className="border-blue-200 bg-blue-50">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-blue-700">
                  <Zap className="h-5 w-5" />
                  Schedule Optimization Available
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-blue-600">
                  Some of your searches have low priority. Consider adjusting their schedule
                  or disabling them to optimize your search budget and performance.
                </p>
                <Button size="sm" variant="outline" className="mt-3">
                  Review Low Priority Searches
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
