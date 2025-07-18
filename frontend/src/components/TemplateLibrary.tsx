import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { templateApi } from '@/lib/api'
import { Search, FileText, Users, Plus } from 'lucide-react'
import { TemplateCard } from './TemplateCard'
import { TemplateDialog } from './TemplateDialog'

export function TemplateLibrary() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [showPopular, setShowPopular] = useState(false)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['templates', {
      search: searchTerm || undefined,
      category: selectedCategory === 'all' ? undefined : selectedCategory,
      popular: showPopular || undefined,
      limit: 50
    }],
    queryFn: () => templateApi.getTemplates({
      search: searchTerm || undefined,
      category: selectedCategory === 'all' ? undefined : selectedCategory,
      popular: showPopular || undefined,
      limit: 50,
    }),
  })

  const { data: categories } = useQuery({
    queryKey: ['template-categories'],
    queryFn: templateApi.getTemplateCategories,
  })

  const clearFilters = () => {
    setSearchTerm('')
    setSelectedCategory('all')
    setShowPopular(false)
  }

  const hasActiveFilters = searchTerm || (selectedCategory !== 'all') || showPopular

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Search Templates</h2>
          <p className="text-muted-foreground">
            Create reusable search configurations and use community templates
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)} className="sm:w-auto">
          <Plus className="mr-2 h-4 w-4" />
          Create Template
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search templates..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* Category Filter */}
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger>
                <SelectValue placeholder="All categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {categories?.map((category) => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Show Popular Toggle */}
            <Button
              variant={showPopular ? 'default' : 'outline'}
              onClick={() => setShowPopular(!showPopular)}
              className="justify-start"
            >
              <Users className="mr-2 h-4 w-4" />
              Popular Only
            </Button>

            {/* Clear Filters */}
            {hasActiveFilters && (
              <Button variant="ghost" onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Templates Grid */}
      {templatesLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-muted rounded w-3/4"></div>
                  <div className="h-3 bg-muted rounded w-1/2"></div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="animate-pulse space-y-3">
                  <div className="h-3 bg-muted rounded"></div>
                  <div className="h-3 bg-muted rounded w-5/6"></div>
                  <div className="flex gap-2">
                    <div className="h-6 bg-muted rounded w-16"></div>
                    <div className="h-6 bg-muted rounded w-12"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : !templates || templates.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              {hasActiveFilters ? 'No templates found' : 'No templates yet'}
            </h3>
            <p className="text-muted-foreground text-center mb-4">
              {hasActiveFilters
                ? 'Try adjusting your search criteria or filters'
                : 'Create your first template to get started'}
            </p>
            {hasActiveFilters ? (
              <Button variant="outline" onClick={clearFilters}>
                Clear Filters
              </Button>
            ) : (
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Template
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {templates.length} template{templates.length !== 1 ? 's' : ''} found
            </p>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </div>

          {/* Templates Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map((template) => (
              <TemplateCard key={template.id} template={template} />
            ))}
          </div>
        </>
      )}

      {/* Create Template Dialog */}
      <TemplateDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
      />
    </div>
  )
}
