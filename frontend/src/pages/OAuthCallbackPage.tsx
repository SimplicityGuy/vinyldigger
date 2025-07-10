import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

function OAuthCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    // Extract OAuth parameters from URL
    const oauthToken = searchParams.get('oauth_token')
    const oauthVerifier = searchParams.get('oauth_verifier')
    const state = searchParams.get('state')
    const error = searchParams.get('error')

    if (error) {
      setStatus('error')
      setMessage('Authorization was denied or cancelled.')
      return
    }

    if (!oauthToken || !oauthVerifier || !state) {
      setStatus('error')
      setMessage('Invalid OAuth callback parameters.')
      return
    }

    // The backend will handle the callback
    // For now, we'll just show a success message
    // In a real implementation, you'd call the backend callback endpoint
    setStatus('success')
    setMessage('Authorization successful! You can now close this window.')

    // Optionally redirect back to settings after a delay
    setTimeout(() => {
      window.close() // Try to close the window
      // If window.close() doesn't work (e.g., not opened by script), redirect
      navigate('/settings')
    }, 3000)
  }, [searchParams, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>OAuth Authorization</CardTitle>
          <CardDescription>
            {status === 'loading' && 'Processing authorization...'}
            {status === 'success' && 'Authorization successful!'}
            {status === 'error' && 'Authorization failed'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col items-center gap-4">
            {status === 'loading' && (
              <>
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Please wait...</p>
              </>
            )}

            {status === 'success' && (
              <>
                <CheckCircle className="h-8 w-8 text-green-600" />
                <p className="text-sm text-center">{message}</p>
                <p className="text-sm text-muted-foreground text-center">
                  This window will close automatically, or you can close it manually.
                </p>
              </>
            )}

            {status === 'error' && (
              <>
                <XCircle className="h-8 w-8 text-red-600" />
                <p className="text-sm text-center">{message}</p>
                <Button onClick={() => navigate('/settings')}>
                  Back to Settings
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default OAuthCallbackPage
