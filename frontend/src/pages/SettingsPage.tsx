import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Key, Settings2, User, AlertCircle, CheckCircle, ExternalLink, Calendar, Edit, Save, X } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import api from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { useAuth } from '@/hooks/useAuth'

function SettingsPage() {
  const { toast } = useToast()
  const { user, isLoading: isUserLoading } = useAuth()
  const queryClient = useQueryClient()
  const [discogsVerificationCode, setDiscogsVerificationCode] = useState('')
  const [discogsState, setDiscogsState] = useState('')
  const [showDiscogsVerificationInput, setShowDiscogsVerificationInput] = useState(false)
  const [ebayAuthorizationCode, setEbayAuthorizationCode] = useState('')
  const [ebayState, setEbayState] = useState('')
  const [showEbayVerificationInput, setShowEbayVerificationInput] = useState(false)
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [isEditingEmail, setIsEditingEmail] = useState(false)
  const [editEmailValue, setEditEmailValue] = useState('')

  // Query OAuth status
  const { data: discogsOAuthStatus, refetch: refetchDiscogsStatus } = useQuery({
    queryKey: ['oauth-status', 'discogs'],
    queryFn: () => api.getOAuthStatus('discogs'),
  })

  // eBay OAuth status
  const { data: ebayOAuthStatus, refetch: refetchEbayStatus } = useQuery({
    queryKey: ['oauth-status', 'ebay'],
    queryFn: () => api.getOAuthStatus('ebay'),
  })

  // OAuth authorization mutations
  const authorizeDiscogsMutation = useMutation({
    mutationFn: () => api.initiateOAuth('discogs'),
    onSuccess: (data) => {
      // Open authorization URL in new window
      window.open(data.authorization_url, '_blank', 'width=600,height=800')
      // Store state and show verification input
      setDiscogsState(data.state)
      setShowDiscogsVerificationInput(true)
    },
  })

  const revokeDiscogsMutation = useMutation({
    mutationFn: () => api.revokeOAuth('discogs'),
    onSuccess: () => {
      refetchDiscogsStatus()
      setShowDiscogsVerificationInput(false)
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
      setShowDiscogsVerificationInput(false)
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

  // eBay OAuth mutations
  const authorizeEbayMutation = useMutation({
    mutationFn: () => api.initiateOAuth('ebay'),
    onSuccess: (data) => {
      // Open authorization URL in new window
      window.open(data.authorization_url, '_blank', 'width=600,height=800')
      // Store state and show verification input
      setEbayState(data.state)
      setShowEbayVerificationInput(true)
    },
  })

  const revokeEbayMutation = useMutation({
    mutationFn: () => api.revokeOAuth('ebay'),
    onSuccess: () => {
      refetchEbayStatus()
      setShowEbayVerificationInput(false)
      setEbayAuthorizationCode('')
      setEbayState('')
    },
  })

  const verifyEbayMutation = useMutation({
    mutationFn: () => api.verifyEbay(ebayState, ebayAuthorizationCode),
    onSuccess: (data) => {
      toast({
        title: 'Success!',
        description: `Connected to eBay as ${data.username}`,
      })
      refetchEbayStatus()
      setShowEbayVerificationInput(false)
      setEbayAuthorizationCode('')
      setEbayState('')
    },
    onError: () => {
      toast({
        title: 'Verification failed',
        description: 'Please check the code and try again.',
        variant: 'destructive',
      })
    },
  })

  const handleAuthorizeDiscogs = () => {
    authorizeDiscogsMutation.mutate()
  }

  const handleRevokeDiscogs = () => {
    if (confirm('Are you sure you want to revoke Discogs access?')) {
      revokeDiscogsMutation.mutate()
    }
  }

  const handleAuthorizeEbay = () => {
    authorizeEbayMutation.mutate()
  }

  const handleRevokeEbay = () => {
    if (confirm('Are you sure you want to revoke eBay access?')) {
      revokeEbayMutation.mutate()
    }
  }

  // User update mutation
  const updateUserMutation = useMutation({
    mutationFn: api.updateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] })
      toast({
        title: 'Email updated',
        description: 'Your email address has been updated successfully.',
      })
      setIsEditingEmail(false)
    },
    onError: () => {
      toast({
        title: 'Update failed',
        description: 'Failed to update email address. Please try again.',
        variant: 'destructive',
      })
    },
  })

  const startEditEmail = () => {
    setEditEmailValue(user?.email || '')
    setIsEditingEmail(true)
  }

  const cancelEditEmail = () => {
    setIsEditingEmail(false)
    setEditEmailValue('')
  }

  const saveEmail = () => {
    if (editEmailValue.trim() && editEmailValue !== user?.email) {
      updateUserMutation.mutate({ email: editEmailValue.trim() })
    } else {
      setIsEditingEmail(false)
    }
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
                {showDiscogsVerificationInput && (
                  <div className="mt-4 p-4 border rounded-lg space-y-3 bg-muted/50">
                    <p className="text-sm font-medium">Enter Verification Code</p>
                    <p className="text-sm text-muted-foreground">
                      After authorizing VinylDigger on Discogs, enter the verification code shown on
                      the Discogs page.
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
                          setShowDiscogsVerificationInput(false)
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

          {/* eBay OAuth */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4" />
                <h3 className="font-medium">eBay</h3>
                {ebayOAuthStatus?.is_authorized && (
                  <span className="flex items-center gap-1 text-sm text-green-600">
                    <CheckCircle className="h-4 w-4" />
                    Connected as {ebayOAuthStatus.username}
                  </span>
                )}
              </div>
            </div>

            {ebayOAuthStatus?.is_authorized ? (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRevokeEbay}
                  disabled={revokeEbayMutation.isPending}
                >
                  Revoke Access
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Connect your eBay account to search their marketplace for vinyl records.
                </p>
                <Button
                  onClick={handleAuthorizeEbay}
                  disabled={authorizeEbayMutation.isPending}
                  className="gap-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  Connect eBay Account
                </Button>
                {authorizeEbayMutation.isError && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" />
                    Failed to start authorization. Please try again.
                  </p>
                )}
                {showEbayVerificationInput && (
                  <div className="mt-4 p-4 border rounded-lg space-y-3 bg-muted/50">
                    <p className="text-sm font-medium">Enter Authorization Code</p>
                    <p className="text-sm text-muted-foreground">
                      After authorizing VinylDigger on eBay, enter the authorization code shown.
                    </p>
                    <div className="flex gap-2">
                      <Input
                        type="text"
                        placeholder="Enter authorization code"
                        value={ebayAuthorizationCode}
                        onChange={(e) => setEbayAuthorizationCode(e.target.value)}
                        className="flex-1"
                      />
                      <Button
                        onClick={() => verifyEbayMutation.mutate()}
                        disabled={!ebayAuthorizationCode || verifyEbayMutation.isPending}
                      >
                        {verifyEbayMutation.isPending ? 'Verifying...' : 'Verify'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setShowEbayVerificationInput(false)
                          setEbayAuthorizationCode('')
                          setEbayState('')
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                    {verifyEbayMutation.isError && (
                      <p className="text-sm text-red-600">
                        Verification failed. Please check the code and try again.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
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
              checked={emailNotifications}
              onChange={(e) => setEmailNotifications(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
          </div>
        </CardContent>
      </Card>

      {/* Account Info */}
      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>Your account details and registration information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!isUserLoading && !user ? (
            <div className="text-center py-4">
              <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Unable to load account information</p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Email</span>
                </div>
                {isUserLoading ? (
                  <Skeleton className="h-4 w-32" />
                ) : isEditingEmail ? (
                  <div className="flex items-center gap-2">
                    <Input
                      value={editEmailValue}
                      onChange={(e) => setEditEmailValue(e.target.value)}
                      type="email"
                      className="h-8 w-48 text-sm"
                      placeholder="Enter email"
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={saveEmail}
                      disabled={updateUserMutation.isPending}
                      className="h-8 w-8 p-0"
                    >
                      <Save className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={cancelEditEmail}
                      className="h-8 w-8 p-0"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{user?.email || 'Not available'}</span>
                    {user?.email && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={startEditEmail}
                        className="h-8 w-8 p-0"
                      >
                        <Edit className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Settings2 className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Account ID</span>
                </div>
                {isUserLoading ? (
                  <Skeleton className="h-3 w-16" />
                ) : user?.id ? (
                  <span className="text-xs font-mono text-muted-foreground">{user.id.slice(0, 8)}</span>
                ) : (
                  <span className="text-xs text-muted-foreground">-</span>
                )}
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Member Since</span>
                </div>
                {isUserLoading ? (
                  <Skeleton className="h-4 w-20" />
                ) : user?.created_at ? (
                  <span className="text-sm text-muted-foreground">
                    {new Date(user.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </span>
                ) : (
                  <span className="text-sm text-muted-foreground">-</span>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default SettingsPage
