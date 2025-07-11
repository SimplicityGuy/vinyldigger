import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Shield, AlertCircle, Save, Trash2, Music, ShoppingBag } from 'lucide-react'
import { useToast } from '@/hooks/useToast'
import { tokenService } from '@/lib/token-service'
import { formatProvider } from '@/lib/utils'

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
  const [discogsData, setDiscogsData] = useState({
    consumer_key: '',
    consumer_secret: '',
    callback_url: '',
  })
  const [ebayData, setEbayData] = useState({
    consumer_key: '',
    consumer_secret: '',
    redirect_uri: '',
    scope: '',
  })

  // Query app configurations
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['admin-app-configs'],
    queryFn: async () => {
      const response = await fetch('/api/v1/admin/app-config', {
        headers: {
          Authorization: `Bearer ${tokenService.getAccessToken()}`,
        },
      })
      if (!response.ok) throw new Error('Failed to fetch configurations')
      return response.json() as Promise<AppConfig[]>
    },
  })

  // Find existing configs
  const discogsConfig = configs.find((c) => c.provider === 'DISCOGS' || c.provider === 'discogs')
  const ebayConfig = configs.find((c) => c.provider === 'EBAY' || c.provider === 'ebay')

  // Mutations
  const updateConfigMutation = useMutation({
    mutationFn: async (data: { provider: string; [key: string]: string }) => {
      const response = await fetch(`/api/v1/admin/app-config/${data.provider}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${tokenService.getAccessToken()}`,
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) throw new Error('Failed to update configuration')
      return response.json()
    },
    onSuccess: (_, variables) => {
      toast({
        title: 'Configuration updated',
        description: `${formatProvider(variables.provider)} configuration has been saved successfully.`,
      })
      queryClient.invalidateQueries({ queryKey: ['admin-app-configs'] })
      // Reset the form
      if (variables.provider.toLowerCase() === 'discogs') {
        setDiscogsData({ consumer_key: '', consumer_secret: '', callback_url: '' })
      } else {
        setEbayData({ consumer_key: '', consumer_secret: '', redirect_uri: '', scope: '' })
      }
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
          Authorization: `Bearer ${tokenService.getAccessToken()}`,
        },
      })
      if (!response.ok) throw new Error('Failed to delete configuration')
      return response.json()
    },
    onSuccess: (_, provider) => {
      toast({
        title: 'Configuration deleted',
        description: `${formatProvider(provider)} configuration has been removed.`,
      })
      queryClient.invalidateQueries({ queryKey: ['admin-app-configs'] })
    },
  })

  const handleDiscogsSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateConfigMutation.mutate({
      provider: 'discogs',
      ...discogsData,
    })
  }

  const handleEbaySubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateConfigMutation.mutate({
      provider: 'ebay',
      ...ebayData,
    })
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

      <div className="grid gap-6 md:grid-cols-2">
        {/* Discogs Configuration */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Music className="h-5 w-5" />
              <CardTitle>Discogs Configuration</CardTitle>
            </div>
            <CardDescription>
              Configure OAuth 1.0a credentials for Discogs API access
            </CardDescription>
          </CardHeader>
          <CardContent>
            {discogsConfig ? (
              <div className="space-y-4">
                <div className="p-3 border rounded-lg">
                  <p className="font-medium">Status: Configured</p>
                  <p className="text-sm text-muted-foreground">
                    Consumer Key: {discogsConfig.consumer_key}
                  </p>
                  {discogsConfig.callback_url && (
                    <p className="text-sm text-muted-foreground">
                      Callback URL: {discogsConfig.callback_url}
                    </p>
                  )}
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteConfigMutation.mutate('discogs')}
                  className="w-full"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Remove Configuration
                </Button>
              </div>
            ) : (
              <form onSubmit={handleDiscogsSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="discogs-key">Consumer Key</Label>
                  <Input
                    id="discogs-key"
                    type="text"
                    value={discogsData.consumer_key}
                    onChange={(e) =>
                      setDiscogsData({ ...discogsData, consumer_key: e.target.value })
                    }
                    placeholder="Enter Discogs consumer key"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="discogs-secret">Consumer Secret</Label>
                  <Input
                    id="discogs-secret"
                    type="password"
                    value={discogsData.consumer_secret}
                    onChange={(e) =>
                      setDiscogsData({ ...discogsData, consumer_secret: e.target.value })
                    }
                    placeholder="Enter Discogs consumer secret"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="discogs-callback">Callback URL (Optional)</Label>
                  <Input
                    id="discogs-callback"
                    type="url"
                    value={discogsData.callback_url}
                    onChange={(e) =>
                      setDiscogsData({ ...discogsData, callback_url: e.target.value })
                    }
                    placeholder="https://yourdomain.com/oauth/callback/discogs"
                  />
                  <p className="text-xs text-muted-foreground">
                    Leave empty for out-of-band (oob) authentication
                  </p>
                </div>

                <Button type="submit" disabled={updateConfigMutation.isPending} className="w-full">
                  <Save className="h-4 w-4 mr-2" />
                  Save Discogs Configuration
                </Button>
              </form>
            )}
          </CardContent>
        </Card>

        {/* eBay Configuration */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShoppingBag className="h-5 w-5" />
              <CardTitle>eBay Configuration</CardTitle>
            </div>
            <CardDescription>Configure OAuth 2.0 credentials for eBay API access</CardDescription>
          </CardHeader>
          <CardContent>
            {ebayConfig ? (
              <div className="space-y-4">
                <div className="p-3 border rounded-lg">
                  <p className="font-medium">Status: Configured</p>
                  <p className="text-sm text-muted-foreground">
                    Client ID: {ebayConfig.consumer_key}
                  </p>
                  {ebayConfig.redirect_uri && (
                    <p className="text-sm text-muted-foreground">
                      Redirect URI: {ebayConfig.redirect_uri}
                    </p>
                  )}
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteConfigMutation.mutate('ebay')}
                  className="w-full"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Remove Configuration
                </Button>
              </div>
            ) : (
              <form onSubmit={handleEbaySubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="ebay-key">Client ID</Label>
                  <Input
                    id="ebay-key"
                    type="text"
                    value={ebayData.consumer_key}
                    onChange={(e) => setEbayData({ ...ebayData, consumer_key: e.target.value })}
                    placeholder="Enter eBay client ID"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="ebay-secret">Client Secret</Label>
                  <Input
                    id="ebay-secret"
                    type="password"
                    value={ebayData.consumer_secret}
                    onChange={(e) => setEbayData({ ...ebayData, consumer_secret: e.target.value })}
                    placeholder="Enter eBay client secret"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="ebay-redirect">Redirect URI</Label>
                  <Input
                    id="ebay-redirect"
                    type="url"
                    value={ebayData.redirect_uri}
                    onChange={(e) => setEbayData({ ...ebayData, redirect_uri: e.target.value })}
                    placeholder="https://yourdomain.com/oauth/callback/ebay"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="ebay-scope">Scopes</Label>
                  <Input
                    id="ebay-scope"
                    type="text"
                    value={ebayData.scope}
                    onChange={(e) => setEbayData({ ...ebayData, scope: e.target.value })}
                    placeholder="https://api.ebay.com/oauth/api_scope"
                  />
                  <p className="text-xs text-muted-foreground">
                    Space-separated list of required scopes
                  </p>
                </div>

                <Button type="submit" disabled={updateConfigMutation.isPending} className="w-full">
                  <Save className="h-4 w-4 mr-2" />
                  Save eBay Configuration
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div>
              <CardTitle className="text-lg">Important Information</CardTitle>
              <CardDescription>About OAuth provider configuration</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <ul className="list-disc list-inside space-y-2 text-sm">
            <li>These credentials are used by all users of the application</li>
            <li>Users will still need to individually authorize access to their accounts</li>
            <li>Keep consumer secrets secure and never expose them publicly</li>
            <li>Discogs uses OAuth 1.0a for authentication</li>
            <li>eBay uses OAuth 2.0 with refresh tokens</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}

export default AdminPage
