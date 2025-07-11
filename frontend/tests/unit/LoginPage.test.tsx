import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
import { LoginPage } from '@/pages/LoginPage'

// Mock useAuth hook
const mockLogin = vi.fn()
const mockNavigate = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    user: null,
    isLoading: false,
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('LoginPage', () => {
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

  const renderLoginPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  it('should render login form', () => {
    renderLoginPage()

    expect(screen.getByText('Welcome to VinylDigger')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText(/Don't have an account/)).toBeInTheDocument()
  })

  it('should handle successful login', async () => {
    const user = userEvent.setup()

    renderLoginPage()

    const emailInput = screen.getByLabelText('Email')
    const passwordInput = screen.getByLabelText('Password')
    const loginButton = screen.getByRole('button', { name: 'Sign in' })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(loginButton)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({ email: 'test@example.com', password: 'password123' })
    })
  })


  it('should disable form while logging in', async () => {
    const user = userEvent.setup()
    mockLogin.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

    renderLoginPage()

    const emailInput = screen.getByLabelText('Email')
    const passwordInput = screen.getByLabelText('Password')
    const loginButton = screen.getByRole('button', { name: 'Sign in' })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(loginButton)

    expect(loginButton).toBeDisabled()
    expect(emailInput).toBeDisabled()
    expect(passwordInput).toBeDisabled()
  })

  it('should navigate to register page when clicking register link', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    const registerLink = screen.getByText('Sign up')
    expect(registerLink).toHaveAttribute('href', '/register')
  })
})