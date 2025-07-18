import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { chainApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { SearchChain, SavedSearch, SearchChainLinkCreate, TriggerCondition } from '@/types/api'
import { Loader2, Plus, X, ArrowRight, Link } from 'lucide-react'

const chainSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name too long'),
  description: z.string().max(500, 'Description too long').optional(),
  is_active: z.boolean().default(true),
})

interface ChainDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  chain?: SearchChain
  availableSearches: SavedSearch[]
}

export function ChainDialog({ open, onOpenChange, chain, availableSearches }: ChainDialogProps) {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [isLoading, setIsLoading] = useState(false)
  const [chainLinks, setChainLinks] = useState<SearchChainLinkCreate[]>(
    chain?.links.map(link => ({
      search_id: link.search_id,
      order_index: link.order_index,
      trigger_condition: link.trigger_condition,
    })) || []
  )

  const form = useForm({
    resolver: zodResolver(chainSchema),
    defaultValues: {
      name: chain?.name || '',
      description: chain?.description || '',
      is_active: chain?.is_active ?? true,
    },
  })

  const createChainMutation = useMutation({
    mutationFn: chainApi.createChain,
    onSuccess: async (newChain) => {
      // Create links after chain is created
      if (chainLinks.length > 0) {
        await Promise.all(
          chainLinks.map(link =>
            chainApi.createChainLink(newChain.id, link)
          )
        )
      }

      queryClient.invalidateQueries({ queryKey: ['chains'] })
      toast({ title: 'Chain created successfully' })
      onOpenChange(false)
      form.reset()
      setChainLinks([])
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to create chain',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const updateChainMutation = useMutation({
    mutationFn: ({ chainId, data }: { chainId: string; data: { name: string; description: string; is_active: boolean } }) =>
      chainApi.updateChain(chainId, data),
    onSuccess: async () => {
      // Update links - for simplicity, we'll delete all and recreate
      if (chain) {
        // Delete existing links
        await Promise.all(
          chain.links.map(link =>
            chainApi.deleteChainLink(chain.id, link.id)
          )
        )

        // Create new links
        await Promise.all(
          chainLinks.map(link =>
            chainApi.createChainLink(chain.id, link)
          )
        )
      }

      queryClient.invalidateQueries({ queryKey: ['chains'] })
      toast({ title: 'Chain updated successfully' })
      onOpenChange(false)
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to update chain',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const onSubmit = async (values: z.infer<typeof chainSchema>) => {
    setIsLoading(true)
    try {
      if (chain) {
        updateChainMutation.mutate({
          chainId: chain.id,
          data: {
            ...values,
            description: values.description || ''
          },
        })
      } else {
        createChainMutation.mutate({
          ...values,
          description: values.description || ''
        })
      }
    } finally {
      setIsLoading(false)
    }
  }

  const addLink = () => {
    setChainLinks([...chainLinks, {
      search_id: '',
      order_index: chainLinks.length,
      trigger_condition: {
        condition_type: 'results_found',
        min_results: 1
      },
    }])
  }

  const removeLink = (index: number) => {
    const newLinks = chainLinks.filter((_, i) => i !== index)
    // Reorder indices
    const reorderedLinks = newLinks.map((link, i) => ({
      ...link,
      order_index: i,
    }))
    setChainLinks(reorderedLinks)
  }

  const updateLink = (index: number, updates: Partial<SearchChainLinkCreate>) => {
    const newLinks = [...chainLinks]
    newLinks[index] = { ...newLinks[index], ...updates }
    setChainLinks(newLinks)
  }

  const moveLink = (index: number, direction: 'up' | 'down') => {
    if (
      (direction === 'up' && index === 0) ||
      (direction === 'down' && index === chainLinks.length - 1)
    ) {
      return
    }

    const newLinks = [...chainLinks]
    const targetIndex = direction === 'up' ? index - 1 : index + 1

    // Swap the links
    const temp = newLinks[index]
    newLinks[index] = newLinks[targetIndex]
    newLinks[targetIndex] = temp

    // Update order indices
    newLinks[index].order_index = index
    newLinks[targetIndex].order_index = targetIndex

    setChainLinks(newLinks)
  }

  const isSubmitting = isLoading || createChainMutation.isPending || updateChainMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link className="h-5 w-5" />
            {chain ? 'Edit Search Chain' : 'Create Search Chain'}
          </DialogTitle>
          <DialogDescription>
            Create a workflow that automatically triggers searches based on results from other searches.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Chain Name</FormLabel>
                    <FormControl>
                      <Input placeholder="My Search Chain" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Describe what this chain does..."
                        className="resize-none"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">Active Chain</FormLabel>
                      <FormDescription>
                        Enable automatic execution of this chain
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>

            {/* Chain Links */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium">Chain Links</h4>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addLink}
                  disabled={availableSearches.length === 0}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Link
                </Button>
              </div>

              {chainLinks.length === 0 ? (
                <Card>
                  <CardContent className="flex items-center justify-center py-8">
                    <div className="text-center">
                      <Link className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">No links configured</p>
                      <p className="text-xs text-muted-foreground">Add links to create a search workflow</p>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {chainLinks.map((link, index) => (
                    <div key={index}>
                      <Card>
                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <Badge variant="outline">Step {index + 1}</Badge>
                              Search Link
                            </CardTitle>
                            <div className="flex items-center gap-1">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => moveLink(index, 'up')}
                                disabled={index === 0}
                              >
                                ↑
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => moveLink(index, 'down')}
                                disabled={index === chainLinks.length - 1}
                              >
                                ↓
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => removeLink(index)}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          {/* Search Selection */}
                          <div>
                            <label className="text-xs font-medium">Target Search</label>
                            <Select
                              value={link.search_id}
                              onValueChange={(value) => updateLink(index, { search_id: value })}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select a search to trigger" />
                              </SelectTrigger>
                              <SelectContent>
                                {availableSearches.map((search) => (
                                  <SelectItem key={search.id} value={search.id}>
                                    {search.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          {/* Trigger Condition */}
                          <div className="space-y-2">
                            <label className="text-xs font-medium">Trigger Condition</label>
                            <div className="grid grid-cols-2 gap-2">
                              <Select
                                value={link.trigger_condition?.condition_type || 'results_found'}
                                onValueChange={(value) =>
                                  updateLink(index, {
                                    trigger_condition: {
                                      condition_type: value as TriggerCondition['condition_type'],
                                      ...(value === 'min_results' && { min_results: link.trigger_condition?.min_results || 1 })
                                    }
                                  })
                                }
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="results_found">Results Found</SelectItem>
                                  <SelectItem value="no_results">No Results</SelectItem>
                                  <SelectItem value="min_results">Min Results</SelectItem>
                                </SelectContent>
                              </Select>

                              {link.trigger_condition?.condition_type === 'min_results' && (
                                <Input
                                  type="number"
                                  min="1"
                                  placeholder="Min count"
                                  value={(link.trigger_condition?.min_results || 1).toString()}
                                  onChange={(e) =>
                                    updateLink(index, {
                                      trigger_condition: {
                                        condition_type: link.trigger_condition?.condition_type || 'min_results',
                                        min_results: parseInt(e.target.value) || 1,
                                      }
                                    })
                                  }
                                />
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Arrow between links */}
                      {index < chainLinks.length - 1 && (
                        <div className="flex justify-center py-2">
                          <ArrowRight className="h-4 w-4 text-muted-foreground" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                {chain ? 'Update' : 'Create'} Chain
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
