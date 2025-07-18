import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Layout } from '@/components/Layout'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { SearchesPage } from '@/pages/SearchesPage'
import { SearchDetailPage } from '@/pages/SearchDetailPage'
import { SearchDealsPage } from '@/pages/SearchDealsPage'
import { SearchOffersPage } from '@/pages/SearchOffersPage'
import SettingsPage from '@/pages/SettingsPage'
import OAuthCallbackPage from '@/pages/OAuthCallbackPage'
import AdminPage from '@/pages/AdminPage'
import { Toaster } from '@/components/ui/toaster'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { Loader2 } from 'lucide-react'

function App() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading VinylDigger...</p>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/dashboard" /> : <LoginPage />}
        />
        <Route
          path="/register"
          element={isAuthenticated ? <Navigate to="/dashboard" /> : <RegisterPage />}
        />

        {/* OAuth callback route (public) */}
        <Route path="/oauth/callback" element={<OAuthCallbackPage />} />

        {/* Protected routes */}
        {isAuthenticated ? (
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/searches" element={<SearchesPage />} />
            <Route path="/searches/:searchId" element={<SearchDetailPage />} />
            <Route path="/searches/:searchId/deals" element={<SearchDealsPage />} />
            <Route path="/searches/:searchId/offers" element={<SearchOffersPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/" element={<Navigate to="/dashboard" />} />
          </Route>
        ) : (
          <Route path="*" element={<Navigate to="/login" />} />
        )}
      </Routes>
      <Toaster />
    </ErrorBoundary>
  )
}

export default App
