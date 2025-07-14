import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RegisterPage } from '@/pages/RegisterPage'
import { useAuth } from '@/hooks/useAuth'

// Mock useAuth hook
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

// Mock the Zod schema properly
vi.mock('@/lib/api', () => ({
  registerSchema: {
    parse: vi.fn((data: unknown) => data),
    _def: {
      typeName: 'ZodObject',
    },
  },
}))

// Mock react-hook-form resolver
vi.mock('@hookform/resolvers/zod', () => ({
  zodResolver: vi.fn(() => (data: unknown) => ({ values: data, errors: {} })),
}))

describe('RegisterPage - Basic Coverage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    vi.mocked(useAuth).mockReturnValue({
      register: vi.fn(),
      isRegisterLoading: false,
    })
  })

  const renderRegisterPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  it('renders register form', () => {
    renderRegisterPage()

    expect(screen.getByText('Create an account')).toBeInTheDocument()
    expect(screen.getByText('Start discovering vinyl records today')).toBeInTheDocument()
  })

  it('renders form fields', () => {
    renderRegisterPage()

    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
  })

  it('renders submit button', () => {
    renderRegisterPage()

    expect(screen.getByRole('button', { name: 'Create account' })).toBeInTheDocument()
  })

  it('renders link to login page', () => {
    renderRegisterPage()

    expect(screen.getByText('Sign in')).toBeInTheDocument()
  })

  it('shows loading state when registration is in progress', () => {
    vi.mocked(useAuth).mockReturnValue({
      register: vi.fn(),
      isRegisterLoading: true,
    })

    renderRegisterPage()

    expect(screen.getByText('Creating account...')).toBeInTheDocument()
  })

  it('disables submit button when loading', () => {
    vi.mocked(useAuth).mockReturnValue({
      register: vi.fn(),
      isRegisterLoading: true,
    })

    renderRegisterPage()

    const submitButton = screen.getByRole('button')
    expect(submitButton).toBeDisabled()
  })
})
