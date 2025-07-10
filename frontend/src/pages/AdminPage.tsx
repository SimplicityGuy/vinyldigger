import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Shield, AlertCircle, Save, Trash2 } from 'lucide-react'
import { useToast } from '@/hooks/useToast'

interface AppConfig {
  provider: string
  consumer_key: string
  callback_url?: string
  redirect_uri?: string
  scope?: string
  is_configured: boolean
}

function AdminPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [editingProvider, setEditingProvider] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    provider: 'discogs',
    consumer_key: '',
    consumer_secret: '',
    callback_url: '',
    redirect_uri: '',
    scope: '',
  })

  // Query app configurations
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['admin-app-configs'],
    queryFn: async () => {
      const response = await fetch('/api/v1/admin/app-config', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      })
      if (!response.ok) throw new Error('Failed to fetch configurations')
      return response.json() as Promise<AppConfig[]>
    },
  })

  // Mutations
  const updateConfigMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const response = await fetch(`/api/v1/admin/app-config/${data.provider}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) throw new Error('Failed to update configuration')
      return response.json()
    },
    onSuccess: () => {
      toast({
        title: 'Configuration updated',
        description: 'OAuth configuration has been saved successfully.',
      })
      queryClient.invalidateQueries({ queryKey: ['admin-app-configs'] })
      setEditingProvider(null)
      resetForm()
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update configuration. Please try again.',
        variant: 'destructive',
      })
    },
  })

  const deleteConfigMutation = useMutation({
    mutationFn: async (provider: string) => {
      const response = await fetch(`/api/v1/admin/app-config/${provider}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      })
      if (!response.ok) throw new Error('Failed to delete configuration')
      return response.json()
    },
    onSuccess: () => {
      toast({
        title: 'Configuration deleted',
        description: 'OAuth configuration has been removed.',
      })
      queryClient.invalidateQueries({ queryKey: ['admin-app-configs'] })
    },
  })

  const resetForm = () => {
    setFormData({
      provider: 'discogs',
      consumer_key: '',
      consumer_secret: '',
      callback_url: '',
      redirect_uri: '',
      scope: '',
    })
  }

  const handleEdit = (provider: string) => {
    setEditingProvider(provider)
    const config = configs.find(c => c.provider === provider)
    if (config) {
      setFormData({
        provider: config.provider,
        consumer_key: '', // Don't pre-fill secrets
        consumer_secret: '',
        callback_url: config.callback_url || '',
        redirect_uri: config.redirect_uri || '',
        scope: config.scope || '',
      })
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateConfigMutation.mutate(formData)
  }

  const handleDelete = (provider: string) => {
    if (confirm(`Are you sure you want to delete the ${provider} configuration?`)) {
      deleteConfigMutation.mutate(provider)
    }
  }

  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Shield className="h-6 w-6" />
        <h1 className="text-2xl font-bold">Admin Settings</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>OAuth Provider Configuration</CardTitle>
          <CardDescription>
            Configure OAuth credentials for external service providers. These settings apply to all users.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Existing Configurations */}
          <div className="space-y-4">
            <h3 className="font-medium">Current Configurations</h3>
            {configs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No OAuth providers configured yet.</p>
            ) : (
              <div className="space-y-2">
                {configs.map((config) => (
                  <div key={config.provider} className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <p className="font-medium capitalize">{config.provider}</p>
                      <p className="text-sm text-muted-foreground">
                        Consumer Key: {config.consumer_key}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEdit(config.provider)}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleDelete(config.provider)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Configuration Form */}
          {(editingProvider || configs.length === 0) && (
            <form onSubmit={handleSubmit} className="space-y-4 border-t pt-4">
              <h3 className="font-medium">
                {editingProvider ? `Edit ${editingProvider} Configuration` : 'Add OAuth Provider'}
              </h3>

              <div className="grid gap-4">
                <div className="space-y-2">
                  <Label htmlFor="provider">Provider</Label>
                  <Select
                    id="provider"
                    value={formData.provider}
                    onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                    disabled={!!editingProvider}
                  >
                    <option value="">Select a provider</option>
                    <option value="discogs">Discogs</option>
                    <option value="ebay">eBay (Coming Soon)</option>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="consumer_key">Consumer Key / Client ID</Label>
                  <Input
                    id="consumer_key"
                    type="text"
                    value={formData.consumer_key}
                    onChange={(e) => setFormData({ ...formData, consumer_key: e.target.value })}
                    placeholder="Enter consumer key"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="consumer_secret">Consumer Secret / Client Secret</Label>
                  <Input
                    id="consumer_secret"
                    type="password"
                    value={formData.consumer_secret}
                    onChange={(e) => setFormData({ ...formData, consumer_secret: e.target.value })}
                    placeholder="Enter consumer secret"
                    required
                  />
                </div>

                {formData.provider === 'discogs' && (
                  <div className="space-y-2">
                    <Label htmlFor="callback_url">Callback URL (Optional)</Label>
                    <Input
                      id="callback_url"
                      type="url"
                      value={formData.callback_url}
                      onChange={(e) => setFormData({ ...formData, callback_url: e.target.value })}
                      placeholder="https://yourdomain.com/oauth/callback/discogs"
                    />
                    <p className="text-xs text-muted-foreground">
                      Leave empty for out-of-band (oob) authentication
                    </p>
                  </div>
                )}

                {formData.provider === 'ebay' && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="redirect_uri">Redirect URI</Label>
                      <Input
                        id="redirect_uri"
                        type="url"
                        value={formData.redirect_uri}
                        onChange={(e) => setFormData({ ...formData, redirect_uri: e.target.value })}
                        placeholder="https://yourdomain.com/oauth/callback/ebay"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="scope">Scopes</Label>
                      <Input
                        id="scope"
                        type="text"
                        value={formData.scope}
                        onChange={(e) => setFormData({ ...formData, scope: e.target.value })}
                        placeholder="https://api.ebay.com/oauth/api_scope"
                      />
                    </div>
                  </>
                )}
              </div>

              <div className="flex gap-2">
                <Button type="submit" disabled={updateConfigMutation.isPending}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Configuration
                </Button>
                {editingProvider && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setEditingProvider(null)
                      resetForm()
                    }}
                  >
                    Cancel
                  </Button>
                )}
              </div>
            </form>
          )}

          <div className="border-t pt-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
              <div className="text-sm text-muted-foreground">
                <p className="font-medium">Important:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>These credentials are used by all users of the application</li>
                  <li>Users will need to individually authorize access to their accounts</li>
                  <li>Keep consumer secrets secure and never expose them publicly</li>
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default AdminPage
