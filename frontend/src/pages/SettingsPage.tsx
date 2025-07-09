import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Key, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { configApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import type { ApiKey } from '@/types/api'

export function SettingsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [apiKeys, setApiKeys] = useState({
    discogs: { key: '', secret: '' },
    ebay: { key: '', secret: '' },
  })

  const { data: existingKeys = [] } = useQuery({
    queryKey: ['api-keys'],
    queryFn: configApi.getApiKeys,
  })

  const { data: preferences } = useQuery({
    queryKey: ['preferences'],
    queryFn: configApi.getPreferences,
  })

  const updateApiKeyMutation = useMutation({
    mutationFn: ({ service, key, secret }: { service: string; key: string; secret?: string }) =>
      configApi.updateApiKey(service, key, secret),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      toast({
        title: 'API key saved',
        description: 'Your API key has been securely stored.',
      })
    },
  })

  const handleSaveApiKey = (service: 'discogs' | 'ebay') => {
    const { key, secret } = apiKeys[service]
    if (!key) {
      toast({
        title: 'Error',
        description: 'API key is required',
        variant: 'destructive',
      })
      return
    }

    updateApiKeyMutation.mutate({ service, key, secret })
    setApiKeys((prev) => ({
      ...prev,
      [service]: { key: '', secret: '' },
    }))
  }

  const hasApiKey = (service: string) => {
    return existingKeys.some((key: ApiKey) => key.service === service)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">
          Configure your API keys and preferences
        </p>
      </div>

      {/* API Keys */}
      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>
            Add your API credentials to connect with external services
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Discogs API */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              <h3 className="font-medium">Discogs API</h3>
              {hasApiKey('discogs') && (
                <span className="text-sm text-green-600">✓ Configured</span>
              )}
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="discogs-key">Consumer Key</Label>
                <Input
                  id="discogs-key"
                  type="password"
                  value={apiKeys.discogs.key}
                  onChange={(e) =>
                    setApiKeys((prev) => ({
                      ...prev,
                      discogs: { ...prev.discogs, key: e.target.value },
                    }))
                  }
                  placeholder={hasApiKey('discogs') ? '••••••••' : 'Enter key'}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="discogs-secret">Consumer Secret</Label>
                <Input
                  id="discogs-secret"
                  type="password"
                  value={apiKeys.discogs.secret}
                  onChange={(e) =>
                    setApiKeys((prev) => ({
                      ...prev,
                      discogs: { ...prev.discogs, secret: e.target.value },
                    }))
                  }
                  placeholder={hasApiKey('discogs') ? '••••••••' : 'Enter secret'}
                />
              </div>
            </div>
            <Button
              onClick={() => handleSaveApiKey('discogs')}
              disabled={updateApiKeyMutation.isPending}
              className="gap-2"
            >
              <Save className="h-4 w-4" />
              Save Discogs Keys
            </Button>
          </div>

          {/* eBay API */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              <h3 className="font-medium">eBay API</h3>
              {hasApiKey('ebay') && (
                <span className="text-sm text-green-600">✓ Configured</span>
              )}
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="ebay-key">Client ID</Label>
                <Input
                  id="ebay-key"
                  type="password"
                  value={apiKeys.ebay.key}
                  onChange={(e) =>
                    setApiKeys((prev) => ({
                      ...prev,
                      ebay: { ...prev.ebay, key: e.target.value },
                    }))
                  }
                  placeholder={hasApiKey('ebay') ? '••••••••' : 'Enter client ID'}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ebay-secret">Client Secret</Label>
                <Input
                  id="ebay-secret"
                  type="password"
                  value={apiKeys.ebay.secret}
                  onChange={(e) =>
                    setApiKeys((prev) => ({
                      ...prev,
                      ebay: { ...prev.ebay, secret: e.target.value },
                    }))
                  }
                  placeholder={hasApiKey('ebay') ? '••••••••' : 'Enter secret'}
                />
              </div>
            </div>
            <Button
              onClick={() => handleSaveApiKey('ebay')}
              disabled={updateApiKeyMutation.isPending}
              className="gap-2"
            >
              <Save className="h-4 w-4" />
              Save eBay Keys
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Search Preferences</CardTitle>
          <CardDescription>
            Default settings for your searches
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Minimum Record Condition</Label>
              <p className="text-sm text-muted-foreground">
                {preferences?.min_record_condition || 'VG+'}
              </p>
            </div>
            <div className="space-y-2">
              <Label>Minimum Sleeve Condition</Label>
              <p className="text-sm text-muted-foreground">
                {preferences?.min_sleeve_condition || 'VG+'}
              </p>
            </div>
            <div className="space-y-2">
              <Label>Seller Location</Label>
              <p className="text-sm text-muted-foreground">
                {preferences?.seller_location_preference || 'US'}
              </p>
            </div>
            <div className="space-y-2">
              <Label>Check Interval</Label>
              <p className="text-sm text-muted-foreground">
                Every {preferences?.check_interval_hours || 24} hours
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
