import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from '@/App'
import { useAuth } from '@/hooks/useAuth'

// Simple mocks
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('@/pages/LoginPage', () => ({
  LoginPage: () => <div>Login Page</div>,
}))

vi.mock('@/pages/RegisterPage', () => ({
  RegisterPage: () => <div>Register Page</div>,
}))

vi.mock('@/pages/DashboardPage', () => ({
  DashboardPage: () => <div>Dashboard Page</div>,
}))

vi.mock('@/pages/OAuthCallbackPage', () => ({
  default: () => <div>OAuth Callback Page</div>,
}))

vi.mock('@/components/Layout', () => ({
  Layout: () => <div>Layout Component</div>,
}))

vi.mock('@/components/ui/toaster', () => ({
  Toaster: () => <div>Toaster Component</div>,
}))

vi.mock('@/components/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

describe('App - Basic Coverage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
  })

  const renderApp = (initialPath = '/') => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialPath]}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  it('shows loading state when auth is loading', () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    })

    renderApp()

    expect(screen.getByText('Loading VinylDigger...')).toBeInTheDocument()
  })

  it('shows login page for unauthenticated users', () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    })

    renderApp('/login')

    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('shows register page for unauthenticated users', () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    })

    renderApp('/register')

    expect(screen.getByText('Register Page')).toBeInTheDocument()
  })

  it('renders toaster component', () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    })

    renderApp()

    expect(screen.getByText('Toaster Component')).toBeInTheDocument()
  })

  it('renders oauth callback page', () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    })

    renderApp('/oauth/callback')

    expect(screen.getByText('OAuth Callback Page')).toBeInTheDocument()
  })
})
