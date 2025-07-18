import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { templateApi } from '@/lib/api'
import { SearchTemplate } from '@/types/api'
import { useToast } from '@/hooks/useToast'
import {
  MoreVertical,
  Play,
  Eye,
  Edit,
  Trash2,
  Copy,
  Users,
  Lock,
  Clock,
  TrendingUp
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { TemplateDialog } from './TemplateDialog'
import { TemplatePreviewDialog } from './TemplatePreviewDialog'
import { TemplateUseDialog } from './TemplateUseDialog'

interface TemplateCardProps {
  template: SearchTemplate
}

export function TemplateCard({ template }: TemplateCardProps) {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [showPreviewDialog, setShowPreviewDialog] = useState(false)
  const [showUseDialog, setShowUseDialog] = useState(false)

  const deleteTemplateMutation = useMutation({
    mutationFn: () => templateApi.deleteTemplate(template.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      toast({ title: 'Template deleted successfully' })
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to delete template',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this template?')) {
      deleteTemplateMutation.mutate()
    }
  }

  const isOwner = template.created_by !== null // Simplified ownership check
  const relativeTime = formatDistanceToNow(new Date(template.created_at), { addSuffix: true })

  return (
    <>
      <Card className="group hover:shadow-md transition-shadow">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="space-y-1 flex-1">
              <CardTitle className="text-lg leading-6 line-clamp-2">
                {template.name}
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-xs">
                  {template.category}
                </Badge>
                {template.is_public ? (
                  <Users className="h-3 w-3 text-muted-foreground" />
                ) : (
                  <Lock className="h-3 w-3 text-muted-foreground" />
                )}
              </div>
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setShowPreviewDialog(true)}>
                  <Eye className="mr-2 h-4 w-4" />
                  Preview
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setShowUseDialog(true)}>
                  <Play className="mr-2 h-4 w-4" />
                  Use Template
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                {isOwner && (
                  <>
                    <DropdownMenuItem onClick={() => setShowEditDialog(true)}>
                      <Edit className="mr-2 h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={handleDelete}
                      className="text-red-600 focus:text-red-600"
                      disabled={deleteTemplateMutation.isPending}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </>
                )}
                {!isOwner && (
                  <DropdownMenuItem>
                    <Copy className="mr-2 h-4 w-4" />
                    Duplicate
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Description */}
          <p className="text-sm text-muted-foreground line-clamp-2">
            {template.description || 'No description provided'}
          </p>

          {/* Template Stats */}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              <span>{template.usage_count} uses</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>{relativeTime}</span>
            </div>
          </div>

          {/* Quick Preview of Template Data */}
          <div className="bg-muted/50 rounded-lg p-3 space-y-2">
            <div className="text-xs font-medium text-muted-foreground">Template Preview:</div>
            <div className="space-y-1">
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {(template.template_data.query as any) && (
                <div className="text-xs">
                  <span className="font-medium">Query:</span>{' '}
                  <span className="text-muted-foreground line-clamp-1">
                    {String(template.template_data.query)}
                  </span>
                </div>
              )}
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {(template.template_data.platform as any) && (
                <div className="text-xs">
                  <span className="font-medium">Platform:</span>{' '}
                  <Badge variant="outline" className="text-xs h-4">
                    {String(template.template_data.platform)}
                  </Badge>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPreviewDialog(true)}
              className="flex-1"
            >
              <Eye className="mr-2 h-3 w-3" />
              Preview
            </Button>
            <Button
              size="sm"
              onClick={() => setShowUseDialog(true)}
              className="flex-1"
            >
              <Play className="mr-2 h-3 w-3" />
              Use
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Dialogs */}
      {isOwner && (
        <TemplateDialog
          open={showEditDialog}
          onOpenChange={setShowEditDialog}
          template={template}
        />
      )}

      <TemplatePreviewDialog
        open={showPreviewDialog}
        onOpenChange={setShowPreviewDialog}
        template={template}
      />

      <TemplateUseDialog
        open={showUseDialog}
        onOpenChange={setShowUseDialog}
        template={template}
      />
    </>
  )
}
