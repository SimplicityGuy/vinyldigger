import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { authApi } from '@/lib/api'
import { tokenService } from '@/lib/token-service'
import React from 'react'
import { MemoryRouter } from 'react-router-dom'

// Mock the API client
vi.mock('@/lib/api', () => ({
  authApi: {
    getMe: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
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
    ;(tokenService.hasValidTokens as any).mockReturnValue(true)
    ;(authApi.getMe as any).mockResolvedValue({ id: '123', email: 'test@example.com' })

    const { result } = renderHook(() => useAuth(), { wrapper })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.user).toBe(null)
  })

  it('should load user when tokens are valid', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    ;(tokenService.hasValidTokens as any).mockReturnValue(true)
    ;(authApi.getMe as any).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.user).toEqual(mockUser)
    })
  })

  it('should handle login', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    ;(tokenService.hasValidTokens as any).mockReturnValue(false)
    ;(authApi.login as any).mockResolvedValue({ access_token: 'token', refresh_token: 'refresh' })
    ;(authApi.getMe as any).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await act(async () => {
      await result.current.login('test@example.com', 'password')
    })

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser)
      expect(authApi.login).toHaveBeenCalledWith('test@example.com', 'password')
    })
  })

  it('should handle login error', async () => {
    ;(tokenService.hasValidTokens as any).mockReturnValue(false)
    ;(authApi.login as any).mockRejectedValue(new Error('Invalid credentials'))

    const { result } = renderHook(() => useAuth(), { wrapper })

    await expect(
      act(async () => {
        await result.current.login('test@example.com', 'wrong-password')
      })
    ).rejects.toThrow('Invalid credentials')

    expect(result.current.user).toBe(null)
  })

  it('should handle register', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    ;(tokenService.hasValidTokens as any).mockReturnValue(false)
    ;(authApi.register as any).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await act(async () => {
      await result.current.register('test@example.com', 'password')
    })

    expect(authApi.register).toHaveBeenCalledWith('test@example.com', 'password')
  })

  it('should handle logout', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    ;(tokenService.hasValidTokens as any).mockReturnValue(true)
    ;(authApi.getMe as any).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser)
    })

    act(() => {
      result.current.logout()
    })

    expect(authApi.logout).toHaveBeenCalled()
    expect(result.current.user).toBe(null)
  })

  it('should handle no tokens on mount', async () => {
    ;(tokenService.hasValidTokens as any).mockReturnValue(false)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.user).toBe(null)
    })

    expect(authApi.getMe).not.toHaveBeenCalled()
  })

  it('should handle getMe error gracefully', async () => {
    ;(tokenService.hasValidTokens as any).mockReturnValue(true)
    ;(authApi.getMe as any).mockRejectedValue(new Error('Unauthorized'))

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.user).toBe(null)
    })
  })
})