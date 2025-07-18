import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { templateApi } from '@/lib/api'
import { SearchTemplate, SearchTemplatePreview } from '@/types/api'
import { useToast } from '@/hooks/useToast'
import { Eye, Loader2, AlertCircle } from 'lucide-react'

interface TemplatePreviewDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  template: SearchTemplate
}

export function TemplatePreviewDialog({ open, onOpenChange, template }: TemplatePreviewDialogProps) {
  const { toast } = useToast()
  const [preview, setPreview] = useState<SearchTemplatePreview | null>(null)
  const [validationResult, setValidationResult] = useState<{
    valid: boolean
    errors?: Record<string, string>
  } | null>(null)

  const form = useForm({
    defaultValues: Object.keys(template.parameters).reduce((acc, paramName) => {
      const param = template.parameters[paramName]
      acc[paramName] = (param as { default?: string | number | boolean; type: string }).default || ((param as { type: string }).type === 'boolean' ? false : '')
      return acc
    }, {} as Record<string, string | number | boolean>)
  })

  const previewMutation = useMutation({
    mutationFn: (parameters: Record<string, string | number | boolean>) =>
      templateApi.previewTemplate(template.id, parameters),
    onSuccess: (data) => {
      setPreview(data)
      setValidationResult(null)
    },
    onError: (error: Error) => {
      toast({
        title: 'Preview failed',
        description: error.message,
        variant: 'destructive',
      })
      setPreview(null)
    },
  })

  const validateMutation = useMutation({
    mutationFn: (parameters: Record<string, string | number | boolean>) =>
      templateApi.validateTemplateParameters(template.id, parameters),
    onSuccess: (data) => {
      setValidationResult(data)
      if (data.valid) {
        // If validation passes, generate preview
        previewMutation.mutate(form.getValues())
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

  const handlePreview = () => {
    const parameters = form.getValues()
    validateMutation.mutate(parameters)
  }

  const renderParameterInput = (paramName: string, paramConfig: { type: string; required?: boolean; description?: string; enum?: string[]; min?: number; max?: number }) => {
    const { type, required, description } = paramConfig

    return (
      <FormField
        key={paramName}
        control={form.control}
        name={paramName}
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
                    checked={field.value}
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
                  {...field}
                  onChange={(e) => field.onChange(parseFloat(e.target.value) || '')}
                />
              ) : (
                <Input
                  placeholder="Enter value..."
                  {...field}
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
  const isLoading = previewMutation.isPending || validateMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Preview Template: {template.name}
          </DialogTitle>
          <DialogDescription>
            {template.description || 'Configure parameters to see how this template will create a search.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Template Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Template Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{template.category}</Badge>
                <Badge variant={template.is_public ? 'default' : 'outline'}>
                  {template.is_public ? 'Public' : 'Private'}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                Used {template.usage_count} times
              </p>
            </CardContent>
          </Card>

          {/* Parameters Form */}
          {hasParameters && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Configure Parameters</CardTitle>
              </CardHeader>
              <CardContent>
                <Form {...form}>
                  <div className="space-y-4">
                    {Object.entries(template.parameters).map(([paramName, paramConfig]) =>
                      renderParameterInput(paramName, paramConfig as { type: string; required?: boolean; description?: string; enum?: string[]; min?: number; max?: number })
                    )}
                  </div>
                </Form>
              </CardContent>
            </Card>
          )}

          {/* Preview Button */}
          <div className="flex justify-center">
            <Button
              onClick={handlePreview}
              disabled={isLoading}
              className="w-full sm:w-auto"
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <Eye className="mr-2 h-4 w-4" />
              Generate Preview
            </Button>
          </div>

          {/* Validation Results */}
          {validationResult && !validationResult.valid && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-4">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-red-500 mt-0.5" />
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-red-700">
                      Validation Issues:
                    </p>
                    <ul className="text-sm text-red-600 space-y-1">
                      {(validationResult as { issues?: string[] }).issues?.map((issue: string, index: number) => (
                        <li key={index}>• {issue}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Preview Results */}
          {preview && (
            <Card className="border-green-200 bg-green-50">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-green-700">
                  Search Preview
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3">
                  <div>
                    <label className="text-xs font-medium text-green-700">Search Name:</label>
                    <p className="text-sm font-medium">{preview.name}</p>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-green-700">Query:</label>
                    <p className="text-sm font-mono bg-background/50 p-2 rounded border">
                      {preview.query}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-green-700">Platform:</label>
                      <Badge variant="outline" className="mt-1">
                        {preview.platform}
                      </Badge>
                    </div>

                    <div>
                      <label className="text-xs font-medium text-green-700">Check Interval:</label>
                      <p className="text-sm">{preview.check_interval_hours} hours</p>
                    </div>
                  </div>

                  {(preview.min_price || preview.max_price) && (
                    <div>
                      <label className="text-xs font-medium text-green-700">Price Range:</label>
                      <p className="text-sm">
                        {preview.min_price ? `$${preview.min_price}` : 'Any'} - {preview.max_price ? `$${preview.max_price}` : 'Any'}
                      </p>
                    </div>
                  )}

                  {Object.keys(preview.filters).length > 0 && (
                    <div>
                      <label className="text-xs font-medium text-green-700">Filters:</label>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {Object.entries(preview.filters).map(([key, value]) => (
                          <Badge key={key} variant="outline" className="text-xs">
                            {key}: {String(value)}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-green-200">
                  <p className="text-xs text-green-600">
                    ✓ This preview shows exactly how the search will be configured when you use this template.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
