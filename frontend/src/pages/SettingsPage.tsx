import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Key, Settings2, User, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react'
import api from '@/lib/api'
import { useToast } from '@/hooks/useToast'

function SettingsPage() {
  const { toast } = useToast()
  const [discogsVerificationCode, setDiscogsVerificationCode] = useState('')
  const [discogsState, setDiscogsState] = useState('')
  const [showVerificationInput, setShowVerificationInput] = useState(false)
  const [preferences, setPreferences] = useState({
    min_record_condition: 'VG+',
    min_sleeve_condition: 'VG+',
    seller_location_preference: 'US',
    check_interval_hours: 24,
    email_notifications: true,
  })

  // Query OAuth status
  const { data: discogsOAuthStatus, refetch: refetchDiscogsStatus } = useQuery({
    queryKey: ['oauth-status', 'discogs'],
    queryFn: () => api.getOAuthStatus('discogs'),
  })

  // eBay OAuth will be added later
  // const { data: ebayOAuthStatus, refetch: refetchEbayStatus } = useQuery({
  //   queryKey: ['oauth-status', 'ebay'],
  //   queryFn: () => api.getOAuthStatus('ebay'),
  // })

  // OAuth authorization mutations
  const authorizeDiscogsMutation = useMutation({
    mutationFn: () => api.initiateOAuth('discogs'),
    onSuccess: (data) => {
      // Open authorization URL in new window
      window.open(data.authorization_url, '_blank', 'width=600,height=800')
      // Store state and show verification input
      setDiscogsState(data.state)
      setShowVerificationInput(true)
    },
  })

  const revokeDiscogsMutation = useMutation({
    mutationFn: () => api.revokeOAuth('discogs'),
    onSuccess: () => {
      refetchDiscogsStatus()
      setShowVerificationInput(false)
      setDiscogsVerificationCode('')
      setDiscogsState('')
    },
  })

  const verifyDiscogsMutation = useMutation({
    mutationFn: () => api.verifyDiscogs(discogsState, discogsVerificationCode),
    onSuccess: (data) => {
      toast({
        title: 'Success!',
        description: `Connected to Discogs as ${data.username}`,
      })
      refetchDiscogsStatus()
      setShowVerificationInput(false)
      setDiscogsVerificationCode('')
      setDiscogsState('')
    },
    onError: () => {
      toast({
        title: 'Verification failed',
        description: 'Please check the code and try again.',
        variant: 'destructive',
      })
    },
  })

  const updatePreferencesMutation = useMutation({
    mutationFn: (prefs: typeof preferences) => api.updatePreferences(prefs),
  })

  const handleAuthorizeDiscogs = () => {
    authorizeDiscogsMutation.mutate()
  }

  const handleRevokeDiscogs = () => {
    if (confirm('Are you sure you want to revoke Discogs access?')) {
      revokeDiscogsMutation.mutate()
    }
  }

  const handleSavePreferences = () => {
    updatePreferencesMutation.mutate(preferences)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Settings2 className="h-6 w-6" />
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>

      {/* OAuth Authorizations */}
      <Card>
        <CardHeader>
          <CardTitle>Platform Authorizations</CardTitle>
          <CardDescription>
            Authorize VinylDigger to access your accounts on different platforms
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Discogs OAuth */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4" />
                <h3 className="font-medium">Discogs</h3>
                {discogsOAuthStatus?.is_authorized && (
                  <span className="flex items-center gap-1 text-sm text-green-600">
                    <CheckCircle className="h-4 w-4" />
                    Connected as {discogsOAuthStatus.username}
                  </span>
                )}
              </div>
            </div>

            {discogsOAuthStatus?.is_authorized ? (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRevokeDiscogs}
                  disabled={revokeDiscogsMutation.isPending}
                >
                  Revoke Access
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Connect your Discogs account to search their marketplace and sync your collection.
                </p>
                <Button
                  onClick={handleAuthorizeDiscogs}
                  disabled={authorizeDiscogsMutation.isPending}
                  className="gap-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  Connect Discogs Account
                </Button>
                {authorizeDiscogsMutation.isError && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" />
                    Failed to start authorization. Please try again.
                  </p>
                )}
                {showVerificationInput && (
                  <div className="mt-4 p-4 border rounded-lg space-y-3 bg-muted/50">
                    <p className="text-sm font-medium">Enter Verification Code</p>
                    <p className="text-sm text-muted-foreground">
                      After authorizing VinylDigger on Discogs, enter the verification code shown on the Discogs page.
                    </p>
                    <div className="flex gap-2">
                      <Input
                        type="text"
                        placeholder="Enter verification code"
                        value={discogsVerificationCode}
                        onChange={(e) => setDiscogsVerificationCode(e.target.value)}
                        className="flex-1"
                      />
                      <Button
                        onClick={() => verifyDiscogsMutation.mutate()}
                        disabled={!discogsVerificationCode || verifyDiscogsMutation.isPending}
                      >
                        {verifyDiscogsMutation.isPending ? 'Verifying...' : 'Verify'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setShowVerificationInput(false)
                          setDiscogsVerificationCode('')
                          setDiscogsState('')
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                    {verifyDiscogsMutation.isError && (
                      <p className="text-sm text-red-600">
                        Verification failed. Please check the code and try again.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* eBay OAuth - Coming Soon */}
          <div className="space-y-2 opacity-50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4" />
                <h3 className="font-medium">eBay</h3>
                <span className="text-sm text-muted-foreground">(Coming Soon)</span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              eBay integration will be available soon.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Search Preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Search Preferences</CardTitle>
          <CardDescription>Configure your default search settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="min-record">Minimum Record Condition</Label>
              <Select
                id="min-record"
                value={preferences.min_record_condition}
                onChange={(e) =>
                  setPreferences((prev) => ({ ...prev, min_record_condition: e.target.value }))
                }
              >
                <option value="M">Mint (M)</option>
                <option value="NM">Near Mint (NM)</option>
                <option value="VG+">Very Good Plus (VG+)</option>
                <option value="VG">Very Good (VG)</option>
                <option value="G+">Good Plus (G+)</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="min-sleeve">Minimum Sleeve Condition</Label>
              <Select
                id="min-sleeve"
                value={preferences.min_sleeve_condition}
                onChange={(e) =>
                  setPreferences((prev) => ({ ...prev, min_sleeve_condition: e.target.value }))
                }
              >
                <option value="M">Mint (M)</option>
                <option value="NM">Near Mint (NM)</option>
                <option value="VG+">Very Good Plus (VG+)</option>
                <option value="VG">Very Good (VG)</option>
                <option value="G+">Good Plus (G+)</option>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="location">Preferred Seller Location</Label>
            <Select
              id="location"
              value={preferences.seller_location_preference}
              onChange={(e) =>
                setPreferences((prev) => ({ ...prev, seller_location_preference: e.target.value }))
              }
            >
              <option value="US">United States</option>
              <option value="EU">Europe</option>
              <option value="UK">United Kingdom</option>
              <option value="ANY">Any Location</option>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="check-interval">Check Interval (hours)</Label>
            <Input
              id="check-interval"
              type="number"
              min={1}
              max={168}
              value={preferences.check_interval_hours}
              onChange={(e) =>
                setPreferences((prev) => ({
                  ...prev,
                  check_interval_hours: parseInt(e.target.value) || 24,
                }))
              }
            />
          </div>
          <Button onClick={handleSavePreferences} disabled={updatePreferencesMutation.isPending}>
            Save Preferences
          </Button>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
          <CardDescription>Configure how you want to be notified</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="notifications">Email Notifications</Label>
              <p className="text-sm text-muted-foreground">
                Receive email alerts when new matches are found
              </p>
            </div>
            <input
              type="checkbox"
              id="notifications"
              checked={preferences.email_notifications}
              onChange={(e) =>
                setPreferences((prev) => ({ ...prev, email_notifications: e.target.checked }))
              }
              className="h-4 w-4 rounded border-gray-300"
            />
          </div>
        </CardContent>
      </Card>

      {/* Account Info */}
      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <User className="h-4 w-4" />
            <span className="text-muted-foreground">Email:</span>
            <span className="font-medium">{/* User email will go here */}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default SettingsPage
