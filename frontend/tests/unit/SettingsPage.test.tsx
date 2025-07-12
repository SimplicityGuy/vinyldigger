import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import SettingsPage from '@/pages/SettingsPage'
import * as authHook from '@/hooks/useAuth'

// Mock the useAuth hook
vi.mock('@/hooks/useAuth')

// Mock the useToast hook
vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock the api module
vi.mock('@/lib/api', () => ({
  default: {
    getOAuthStatus: vi.fn().mockResolvedValue({ is_connected: false }),
    initiateOAuth: vi.fn(),
    revokeOAuth: vi.fn(),
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('SettingsPage', () => {
  it('displays user email when user data is loaded', async () => {
    const mockUser = {
      id: '12345678-1234-1234-1234-123456789012',
      email: 'test@example.com',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    vi.mocked(authHook.useAuth).mockReturnValue({
      user: mockUser,
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      isLoginLoading: false,
      isRegisterLoading: false,
    })

    render(<SettingsPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('test@example.com')).toBeInTheDocument()
    })

    // Also check that Account ID is displayed
    expect(screen.getByText('12345678')).toBeInTheDocument()

    // Check that the date is displayed (format may vary by timezone)
    const dateElement = screen.getByText(/\w{3} \d{1,2}, \d{4}/)
    expect(dateElement).toBeInTheDocument()
  })

  it('displays loading skeletons when user data is loading', () => {
    vi.mocked(authHook.useAuth).mockReturnValue({
      user: null,
      isLoading: true,
      isAuthenticated: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      isLoginLoading: false,
      isRegisterLoading: false,
    })

    const { container } = render(<SettingsPage />, { wrapper: createWrapper() })

    // Check for skeleton elements
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('displays error message when user data cannot be loaded', () => {
    vi.mocked(authHook.useAuth).mockReturnValue({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      isLoginLoading: false,
      isRegisterLoading: false,
    })

    render(<SettingsPage />, { wrapper: createWrapper() })

    expect(screen.getByText('Unable to load account information')).toBeInTheDocument()
  })
})
