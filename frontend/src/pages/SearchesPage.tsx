import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Play, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { searchApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'

export function SearchesPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)

  const { data: searches = [], isLoading } = useQuery({
    queryKey: ['searches'],
    queryFn: searchApi.getSearches,
  })

  const runSearchMutation = useMutation({
    mutationFn: searchApi.runSearch,
    onSuccess: () => {
      toast({
        title: 'Search started',
        description: 'Your search is running in the background.',
      })
    },
  })

  const deleteSearchMutation = useMutation({
    mutationFn: searchApi.deleteSearch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['searches'] })
      toast({
        title: 'Search deleted',
        description: 'The search has been removed.',
      })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Searches</h2>
          <p className="text-muted-foreground">
            Manage your saved searches and view results
          </p>
        </div>
        <Button onClick={() => setIsCreating(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          New Search
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : searches.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground mb-4">No searches yet</p>
            <Button onClick={() => setIsCreating(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Create your first search
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {searches.map((search: any) => (
            <Card key={search.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{search.name}</CardTitle>
                    <CardDescription>
                      {search.query} • {search.platform} • Every{' '}
                      {search.check_interval_hours} hours
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => runSearchMutation.mutate(search.id)}
                      disabled={runSearchMutation.isPending}
                      className="gap-2"
                    >
                      <Play className="h-3 w-3" />
                      Run
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => deleteSearchMutation.mutate(search.id)}
                      disabled={deleteSearchMutation.isPending}
                      className="gap-2 text-destructive hover:bg-destructive hover:text-destructive-foreground"
                    >
                      <Trash2 className="h-3 w-3" />
                      Delete
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Last checked:{' '}
                  {search.last_checked_at
                    ? new Date(search.last_checked_at).toLocaleString()
                    : 'Never'}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}