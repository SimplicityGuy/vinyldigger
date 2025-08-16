import { useState } from 'react'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
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
import { templateApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { SearchTemplate, SearchTemplateUpdate } from '@/types/api'
import { Loader2, Plus, X } from 'lucide-react'

const templateSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name too long'),
  description: z.string().max(500, 'Description too long'),
  category: z.string().min(1, 'Category is required'),
  is_public: z.boolean().default(false),
  template_data: z.object({
    query: z.string().min(1, 'Query is required'),
    platform: z.enum(['discogs', 'ebay', 'both']),
    min_price: z.number().optional(),
    max_price: z.number().optional(),
    check_interval_hours: z.number().min(1).default(24),
  }),
  parameters: z.record(z.object({
    type: z.enum(['string', 'number', 'boolean']),
    required: z.boolean().default(false),
    default: z.any().optional(),
    description: z.string().optional(),
  })).default({}),
})

interface TemplateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  template?: SearchTemplate
}

export function TemplateDialog({ open, onOpenChange, template }: TemplateDialogProps) {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [isLoading, setIsLoading] = useState(false)
  const [newParameterName, setNewParameterName] = useState('')

  const { data: categories } = useQuery({
    queryKey: ['template-categories'],
    queryFn: templateApi.getTemplateCategories,
  })

  const form = useForm({
    resolver: zodResolver(templateSchema),
    defaultValues: {
      name: template?.name || '',
      description: template?.description || '',
      category: template?.category || '',
      is_public: template?.is_public || false,
      template_data: {
        query: template?.template_data.query || '',
        platform: template?.template_data.platform || 'both',
        min_price: template?.template_data.min_price || undefined,
        max_price: template?.template_data.max_price || undefined,
        check_interval_hours: template?.template_data.check_interval_hours || 24,
      },
      parameters: template?.parameters || {},
    },
  })

  const createTemplateMutation = useMutation({
    mutationFn: templateApi.createTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      queryClient.invalidateQueries({ queryKey: ['template-categories'] })
      toast({ title: 'Template created successfully' })
      onOpenChange(false)
      form.reset()
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to create template',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const updateTemplateMutation = useMutation({
    mutationFn: ({ templateId, data }: { templateId: string; data: SearchTemplateUpdate }) =>
      templateApi.updateTemplate(templateId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      queryClient.invalidateQueries({ queryKey: ['template-categories'] })
      toast({ title: 'Template updated successfully' })
      onOpenChange(false)
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to update template',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const onSubmit = async (values: z.infer<typeof templateSchema>) => {
    setIsLoading(true)
    try {
      if (template) {
        updateTemplateMutation.mutate({
          templateId: template.id,
          data: values,
        })
      } else {
        createTemplateMutation.mutate(values)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const addParameter = () => {
    if (!newParameterName.trim()) return

    const currentParameters = form.getValues('parameters')
    form.setValue('parameters', {
      ...currentParameters,
      [newParameterName]: {
        type: 'string',
        required: false,
        description: '',
      },
    })
    setNewParameterName('')
  }

  const removeParameter = (paramName: string) => {
    const currentParameters = form.getValues('parameters') || {}
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { [paramName]: _, ...rest } = currentParameters
    form.setValue('parameters', rest)
  }

  const parameters = form.watch('parameters')
  const isSubmitting = isLoading || createTemplateMutation.isPending || updateTemplateMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {template ? 'Edit Template' : 'Create Search Template'}
          </DialogTitle>
          <DialogDescription>
            Create a reusable search template with parameters that can be customized when used.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Basic Information */}
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Template Name</FormLabel>
                    <FormControl>
                      <Input placeholder="My Search Template" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="category"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Category</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select category" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {categories?.map((category) => (
                          <SelectItem key={category} value={category}>
                            {category}
                          </SelectItem>
                        ))}
                        <SelectItem value="Rock">Rock</SelectItem>
                        <SelectItem value="Jazz">Jazz</SelectItem>
                        <SelectItem value="Electronic">Electronic</SelectItem>
                        <SelectItem value="Hip-Hop">Hip-Hop</SelectItem>
                        <SelectItem value="General">General</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Describe what this template searches for..."
                      className="resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Template Data */}
            <div className="space-y-4">
              <h4 className="text-sm font-medium">Search Configuration</h4>

              <FormField
                control={form.control}
                name="template_data.query"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Search Query</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g., {artist} {album} OR use variables like {{genre}}"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Use {'{variable}'} syntax for parameters that users can customize
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-3 gap-4">
                <FormField
                  control={form.control}
                  name="template_data.platform"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Platform</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="both">Both</SelectItem>
                          <SelectItem value="discogs">Discogs</SelectItem>
                          <SelectItem value="ebay">eBay</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="template_data.min_price"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Min Price ($)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="0.00"
                          {...field}
                          onChange={(e) => field.onChange(parseFloat(e.target.value) || undefined)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="template_data.max_price"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Price ($)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="100.00"
                          {...field}
                          onChange={(e) => field.onChange(parseFloat(e.target.value) || undefined)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="template_data.check_interval_hours"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Check Interval (hours)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="1"
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value) || 24)}
                      />
                    </FormControl>
                    <FormDescription>
                      How often to run this search when used
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Parameters */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium">Template Parameters</h4>
                <div className="flex gap-2">
                  <Input
                    placeholder="Parameter name"
                    value={newParameterName}
                    onChange={(e) => setNewParameterName(e.target.value)}
                    className="w-32"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addParameter}
                    disabled={!newParameterName.trim()}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {Object.keys(parameters || {}).length > 0 && (
                <div className="space-y-3">
                  {Object.entries(parameters || {}).map(([paramName, paramConfig]) => (
                    <div key={paramName} className="border rounded-lg p-3 space-y-3">
                      <div className="flex items-center justify-between">
                        <Badge variant="outline">{paramName}</Badge>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeParameter(paramName)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <Select
                            value={paramConfig.type}
                          onValueChange={(value) => {
                            form.setValue(`parameters.${paramName}.type`, value as 'string' | 'number' | 'boolean')
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="string">Text</SelectItem>
                            <SelectItem value="number">Number</SelectItem>
                            <SelectItem value="boolean">Yes/No</SelectItem>
                          </SelectContent>
                        </Select>

                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={paramConfig.required || false}
                            onCheckedChange={(checked) => {
                              form.setValue(`parameters.${paramName}.required`, checked)
                            }}
                          />
                          <label className="text-sm">Required</label>
                        </div>
                      </div>

                      <Input
                        placeholder="Parameter description"
                        value={paramConfig.description || ''}
                        onChange={(e) => {
                          form.setValue(`parameters.${paramName}.description`, e.target.value)
                        }}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Public Template */}
            <FormField
              control={form.control}
              name="is_public"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Public Template</FormLabel>
                    <FormDescription>
                      Make this template available to all users
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
                {template ? 'Update' : 'Create'} Template
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
