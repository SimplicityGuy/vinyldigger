import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
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
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { templateApi } from '@/lib/api'
import { SearchTemplate, TemplateParameter } from '@/types/api'
import { useToast } from '@/hooks/useToast'
import { Play, Loader2, AlertCircle } from 'lucide-react'

interface TemplateUseDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  template: SearchTemplate
}

export function TemplateUseDialog({ open, onOpenChange, template }: TemplateUseDialogProps) {
  const { toast } = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  type FormData = {
    search_name: string
  } & Record<string, string | number | boolean>

  const form = useForm<FormData>({
    defaultValues: {
      search_name: `Search from ${template.name}`,
      ...Object.keys(template.parameters).reduce((acc, paramName) => {
        const param = template.parameters[paramName]
        acc[paramName] = param.default || (param.type === 'boolean' ? false : '')
        return acc
      }, {} as Record<string, string | number | boolean>)
    }
  })

  const validateMutation = useMutation({
    mutationFn: (parameters: Record<string, string | number | boolean>) =>
      templateApi.validateTemplateParameters(template.id, parameters),
    onSuccess: (data) => {
      if (data.valid) {
        setValidationErrors([])
        // Proceed with creating the search
        createSearchMutation.mutate()
      } else {
        setValidationErrors(data.issues)
      }
    },
    onError: (error: Error) => {
      toast({
        title: 'Validation failed',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const createSearchMutation = useMutation({
    mutationFn: () => {
      const { search_name, ...parameters } = form.getValues()
      return templateApi.useTemplate(template.id, {
        template_id: template.id,
        parameters,
        name: search_name,
      })
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['searches'] })
      queryClient.invalidateQueries({ queryKey: ['templates'] }) // Refresh to update usage count
      toast({
        title: 'Search created successfully',
        description: `Created "${form.getValues().search_name}" from template`
      })
      onOpenChange(false)
      // Navigate to the new search
      navigate(`/searches/${data.search_id}`)
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to create search',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const handleSubmit = () => {
    const formValues = form.getValues()
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { search_name: _, ...parameters } = formValues
    setValidationErrors([])

    // Validate parameters if the template has any
    if (Object.keys(template.parameters).length > 0) {
      validateMutation.mutate(parameters)
    } else {
      // No parameters to validate, create search directly
      createSearchMutation.mutate()
    }
  }

  const renderParameterInput = (paramName: string, paramConfig: TemplateParameter) => {
    const { type, required, description } = paramConfig

    return (
      <FormField
        key={paramName}
        control={form.control}
        name={paramName as keyof FormData}
        render={({ field }) => (
          <FormItem>
            <FormLabel className="flex items-center gap-2">
              {paramName}
              {required && <Badge variant="destructive" className="text-xs">Required</Badge>}
            </FormLabel>
            <FormControl>
              {type === 'boolean' ? (
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={Boolean(field.value)}
                    onCheckedChange={field.onChange}
                  />
                  <span className="text-sm text-muted-foreground">
                    {field.value ? 'Yes' : 'No'}
                  </span>
                </div>
              ) : type === 'number' ? (
                <Input
                  type="number"
                  placeholder="Enter number..."
                  value={typeof field.value === 'number' ? field.value.toString() : ''}
                  onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                />
              ) : (
                <Input
                  placeholder="Enter value..."
                  value={field.value as string}
                  onChange={field.onChange}
                />
              )}
            </FormControl>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
            <FormMessage />
          </FormItem>
        )}
      />
    )
  }

  const hasParameters = Object.keys(template.parameters).length > 0
  const isLoading = validateMutation.isPending || createSearchMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            Use Template: {template.name}
          </DialogTitle>
          <DialogDescription>
            Configure the template parameters to create a new search.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <div className="space-y-6">
            {/* Search Name */}
            <FormField
              control={form.control}
              name={'search_name'}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Search Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Enter a name for your search..."
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Template Parameters */}
            {hasParameters && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-medium">Template Parameters</h4>
                  <Badge variant="outline" className="text-xs">
                    {Object.keys(template.parameters).length} parameters
                  </Badge>
                </div>

                <div className="space-y-4">
                  {Object.entries(template.parameters).map(([paramName, paramConfig]) =>
                    renderParameterInput(paramName, paramConfig)
                  )}
                </div>
              </div>
            )}

            {/* Validation Errors */}
            {validationErrors.length > 0 && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-red-500 mt-0.5" />
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-red-700">
                      Please fix the following issues:
                    </p>
                    <ul className="text-sm text-red-600 space-y-1">
                      {validationErrors.map((error, index) => (
                        <li key={index}>• {error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Template Info */}
            <div className="bg-muted/50 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{template.category}</Badge>
                <span className="text-xs text-muted-foreground">
                  Used {template.usage_count} times
                </span>
              </div>
              {template.description && (
                <p className="text-sm text-muted-foreground">
                  {template.description}
                </p>
              )}
            </div>
          </div>
        </Form>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading}
          >
            {isLoading && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Create Search
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
