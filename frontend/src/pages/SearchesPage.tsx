import { useState, memo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Play, Trash2, BarChart3, Edit, Eye, TrendingDown } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { searchApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { formatProvider } from '@/lib/utils'
import type { Search } from '@/types/api'

interface SearchFormData {
  name: string
  query: string
  platform: 'ebay' | 'discogs' | 'both'
  check_interval_hours: number
  min_record_condition?: string
  min_sleeve_condition?: string
  seller_location_preference?: string
}

function SearchesPageComponent() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)
  const [editingSearch, setEditingSearch] = useState<Search | null>(null)
  const [runningSearchId, setRunningSearchId] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<SearchFormData>({
    defaultValues: {
      platform: 'both',
      check_interval_hours: 24,
      min_record_condition: 'VG+',
      min_sleeve_condition: 'VG+',
      seller_location_preference: 'US',
    },
  })

  const { data: searches = [], isLoading } = useQuery({
    queryKey: ['searches'],
    queryFn: searchApi.getSearches,
  })

  const runSearchMutation = useMutation({
    mutationFn: searchApi.runSearch,
    onMutate: (searchId: string) => {
      setRunningSearchId(searchId)
    },
    onSuccess: () => {
      toast({
        title: 'Search started',
        description: 'Your search is running in the background.',
      })
    },
    onSettled: () => {
      setRunningSearchId(null)
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
    onError: (error: unknown) => {
      console.error('Delete search error:', error)
      toast({
        title: 'Error',
        description: 'Failed to delete search. Please try again.',
        variant: 'destructive',
      })
    },
  })

  const createSearchMutation = useMutation({
    mutationFn: searchApi.createSearch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['searches'] })
      toast({
        title: 'Search created',
        description: 'Your search has been saved.',
      })
      setIsCreating(false)
      reset()
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to create search. Please try again.',
        variant: 'destructive',
      })
    },
  })

  const updateSearchMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: SearchFormData }) =>
      searchApi.updateSearch(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['searches'] })
      toast({
        title: 'Search updated',
        description: 'Your search has been updated.',
      })
      setEditingSearch(null)
      reset()
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update search. Please try again.',
        variant: 'destructive',
      })
    },
  })

  const startEdit = (search: Search) => {
    setEditingSearch(search)
    setValue('name', search.name)
    setValue('query', search.query)
    setValue('platform', search.platform)
    setValue('check_interval_hours', search.check_interval_hours)
    setValue('min_record_condition', search.min_record_condition || 'VG+')
    setValue('min_sleeve_condition', search.min_sleeve_condition || 'VG+')
    setValue('seller_location_preference', search.seller_location_preference || 'US')
  }

  const onSubmit = (data: SearchFormData) => {
    if (editingSearch) {
      updateSearchMutation.mutate({ id: editingSearch.id, data })
    } else {
      createSearchMutation.mutate(data)
    }
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Searches</h2>
            <p className="text-muted-foreground">Manage your saved searches and view results</p>
          </div>
          <Button
            onClick={() => setIsCreating(true)}
            className="gap-2"
            aria-label="Create a new search"
          >
            <Plus className="h-4 w-4" />
            New Search
          </Button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8" role="status" aria-label="Loading searches">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            <span className="sr-only">Loading searches...</span>
          </div>
        ) : searches.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-muted-foreground mb-4">No searches yet</p>
              <Button
                onClick={() => setIsCreating(true)}
                className="gap-2"
                aria-label="Create your first search"
              >
                <Plus className="h-4 w-4" />
                Create your first search
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {searches.map((search: Search) => (
              <Card key={search.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>{search.name}</CardTitle>
                      <CardDescription>
                        {search.query} • {formatProvider(search.platform)} • Every{' '}
                        {search.check_interval_hours} hours
                      </CardDescription>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => runSearchMutation.mutate(search.id)}
                        disabled={runningSearchId === search.id}
                        className="gap-2"
                      >
                        <Play className="h-3 w-3" />
                        {runningSearchId === search.id ? 'Running...' : 'Run'}
                      </Button>
                      <Button size="sm" variant="outline" asChild className="gap-2">
                        <Link to={`/searches/${search.id}`}>
                          <Eye className="h-3 w-3" />
                          View
                        </Link>
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => startEdit(search)}
                        className="gap-2"
                      >
                        <Edit className="h-3 w-3" />
                        Edit
                      </Button>
                      <Button size="sm" variant="outline" asChild className="gap-2">
                        <Link to={`/searches/${search.id}/deals`}>
                          <BarChart3 className="h-3 w-3" />
                          Deals
                        </Link>
                      </Button>
                      <Button size="sm" variant="outline" asChild className="gap-2">
                        <Link to={`/searches/${search.id}/offers`}>
                          <TrendingDown className="h-3 w-3" />
                          Offers
                        </Link>
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
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <p>
                      Last checked:{' '}
                      {search.last_run_at ? new Date(search.last_run_at).toLocaleString() : 'Never'}
                    </p>
                    {(search.min_record_condition ||
                      search.min_sleeve_condition ||
                      search.seller_location_preference) && (
                      <p>
                        {search.min_record_condition &&
                          `Min Record: ${search.min_record_condition}`}
                        {search.min_record_condition && search.min_sleeve_condition && ' • '}
                        {search.min_sleeve_condition &&
                          `Min Sleeve: ${search.min_sleeve_condition}`}
                        {(search.min_record_condition || search.min_sleeve_condition) &&
                          search.seller_location_preference &&
                          ' • '}
                        {search.seller_location_preference &&
                          `Location: ${search.seller_location_preference}`}
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog
        open={isCreating || !!editingSearch}
        onOpenChange={(open) => {
          if (!open) {
            setIsCreating(false)
            setEditingSearch(null)
            reset()
          }
        }}
      >
        <DialogContent>
          <DialogClose
            onClose={() => {
              setIsCreating(false)
              setEditingSearch(null)
              reset()
            }}
          />
          <DialogHeader>
            <DialogTitle>{editingSearch ? 'Edit Search' : 'Create New Search'}</DialogTitle>
            <DialogDescription>
              {editingSearch
                ? 'Update your search settings and preferences.'
                : 'Set up a new search to monitor for vinyl records.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <Label htmlFor="name">Search Name</Label>
              <Input
                id="name"
                {...register('name', { required: 'Name is required' })}
                placeholder="e.g., Beatles First Pressings"
              />
              {errors.name && (
                <p className="text-sm text-destructive mt-1">{errors.name.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="query">Search Query</Label>
              <Input
                id="query"
                {...register('query', { required: 'Query is required' })}
                placeholder="e.g., Beatles White Album first pressing"
              />
              {errors.query && (
                <p className="text-sm text-destructive mt-1">{errors.query.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="platform">Platform</Label>
              <Select id="platform" {...register('platform')}>
                <option value="both">Both</option>
                <option value="discogs">Discogs Only</option>
                <option value="ebay">eBay Only</option>
              </Select>
            </div>
            <div>
              <Label htmlFor="check_interval_hours">Check Interval (hours)</Label>
              <Input
                id="check_interval_hours"
                type="number"
                {...register('check_interval_hours', {
                  required: 'Interval is required',
                  min: { value: 1, message: 'Minimum interval is 1 hour' },
                  max: { value: 168, message: 'Maximum interval is 168 hours (1 week)' },
                  valueAsNumber: true,
                })}
                placeholder="24"
              />
              {errors.check_interval_hours && (
                <p className="text-sm text-destructive mt-1">
                  {errors.check_interval_hours.message}
                </p>
              )}
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="min_record_condition">Minimum Record Condition</Label>
                <Select id="min_record_condition" {...register('min_record_condition')}>
                  <option value="M">Mint (M)</option>
                  <option value="NM">Near Mint (NM)</option>
                  <option value="VG+">Very Good Plus (VG+)</option>
                  <option value="VG">Very Good (VG)</option>
                  <option value="G+">Good Plus (G+)</option>
                </Select>
              </div>
              <div>
                <Label htmlFor="min_sleeve_condition">Minimum Sleeve Condition</Label>
                <Select id="min_sleeve_condition" {...register('min_sleeve_condition')}>
                  <option value="M">Mint (M)</option>
                  <option value="NM">Near Mint (NM)</option>
                  <option value="VG+">Very Good Plus (VG+)</option>
                  <option value="VG">Very Good (VG)</option>
                  <option value="G+">Good Plus (G+)</option>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="seller_location_preference">Preferred Seller Location</Label>
              <Select id="seller_location_preference" {...register('seller_location_preference')}>
                <option value="US">United States</option>
                <option value="EU">Europe</option>
                <option value="UK">United Kingdom</option>
                <option value="ANY">Any Location</option>
              </Select>
            </div>
            <div className="flex justify-end gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsCreating(false)
                  setEditingSearch(null)
                  reset()
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createSearchMutation.isPending || updateSearchMutation.isPending}
              >
                {editingSearch
                  ? updateSearchMutation.isPending
                    ? 'Updating...'
                    : 'Update Search'
                  : createSearchMutation.isPending
                    ? 'Creating...'
                    : 'Create Search'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

export const SearchesPage = memo(SearchesPageComponent)
