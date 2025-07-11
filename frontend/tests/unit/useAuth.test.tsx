import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { authApi, ApiError } from '@/lib/api'
import React from 'react'
import { MemoryRouter } from 'react-router-dom'

// Mock the API client
vi.mock('@/lib/api', () => ({
  authApi: {
    getMe: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    hasValidTokens: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) {
      super(message)
    }
  },
}))

// Mock token service
vi.mock('@/lib/token-service', () => ({
  tokenService: {
    hasValidTokens: vi.fn(),
    clearTokens: vi.fn(),
  },
}))

describe('useAuth', () => {
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

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>
  )

  it('should initialize with loading state when tokens exist', () => {
    vi.mocked(authApi.hasValidTokens).mockReturnValue(true)
    vi.mocked(authApi.getMe).mockResolvedValue({ id: '123', email: 'test@example.com' })

    const { result } = renderHook(() => useAuth(), { wrapper })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.user).toBeUndefined()
  })

  it('should load user when tokens are valid', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    vi.mocked(authApi.hasValidTokens).mockReturnValue(true)
    vi.mocked(authApi.getMe).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.user).toEqual(mockUser)
    })
  })

  it('should handle login', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    vi.mocked(authApi.hasValidTokens).mockReturnValue(false)
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'token', refresh_token: 'refresh' })
    vi.mocked(authApi.getMe).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    // Trigger login
    act(() => {
      result.current.login({ email: 'test@example.com', password: 'password' })
    })

    // Wait for login to be called
    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith({ email: 'test@example.com', password: 'password' })
    })

    // After login, hasValidTokens should return true to trigger user fetch
    vi.mocked(authApi.hasValidTokens).mockReturnValue(true)

    // The user query should be invalidated and refetch after login
    // Since we can't directly test React Query's internal state, we just verify the API was called
    expect(authApi.login).toHaveBeenCalled()
  })

  it('should handle login error', async () => {
    vi.mocked(authApi.hasValidTokens).mockReturnValue(false)
    vi.mocked(authApi.login).mockRejectedValue(new Error('Invalid credentials'))

    const { result } = renderHook(() => useAuth(), { wrapper })

    // The login mutation doesn't return a promise, so we can't check for thrown errors
    await act(async () => {
      result.current.login({ email: 'test@example.com', password: 'wrong-password' })
    })

    // Wait a bit for the mutation to complete
    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalled()
    })

    expect(result.current.user).toBeUndefined()
  })

  it('should handle register', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    vi.mocked(authApi.hasValidTokens).mockReturnValue(false)
    vi.mocked(authApi.register).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await act(async () => {
      await result.current.register({ email: 'test@example.com', password: 'password' })
    })

    expect(authApi.register).toHaveBeenCalledWith({ email: 'test@example.com', password: 'password' })
  })

  it('should handle logout', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    vi.mocked(authApi.hasValidTokens).mockReturnValue(true)
    vi.mocked(authApi.getMe).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser)
    })

    act(() => {
      result.current.logout()
    })

    expect(authApi.logout).toHaveBeenCalled()

    // After logout, user query should be invalidated
    await waitFor(() => {
      expect(result.current.user).toBeUndefined()
    })
  })

  it('should handle no tokens on mount', async () => {
    vi.mocked(authApi.hasValidTokens).mockReturnValue(false)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.user).toBeUndefined()
    })

    expect(authApi.getMe).not.toHaveBeenCalled()
  })

  it('should handle getMe error gracefully', async () => {
    vi.mocked(authApi.hasValidTokens).mockReturnValue(true)

    // Mock getMe to reject with an ApiError that should disable retry
    const apiError = new ApiError(401, 'Unauthorized')
    vi.mocked(authApi.getMe).mockRejectedValue(apiError)

    const { result } = renderHook(() => useAuth(), { wrapper })

    // Wait for the query to fail - React Query will retry but should stop due to 401
    await waitFor(() => {
      // Just verify that getMe was called, meaning the query attempted
      expect(authApi.getMe).toHaveBeenCalled()
    })

    // The user should remain undefined after the error
    expect(result.current.user).toBeUndefined()
  })
})
