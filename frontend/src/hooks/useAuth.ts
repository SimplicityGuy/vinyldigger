import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authApi, ApiError } from '@/lib/api'
import { useToast } from './useToast'

export function useAuth() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { toast } = useToast()

  const { data: user, isLoading } = useQuery({
    queryKey: ['user'],
    queryFn: authApi.getMe,
    retry: (failureCount, error) => {
      // Don't retry on 401/403
      if (error instanceof ApiError && [401, 403].includes(error.status)) {
        return false
      }
      return failureCount < 2
    },
    enabled: authApi.hasValidTokens(),
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
  })

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] })
      navigate('/dashboard')
      toast({
        title: 'Welcome back!',
        description: 'You have successfully logged in.',
      })
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError
        ? error.message
        : error instanceof Error
          ? error.message
          : 'Invalid credentials'

      toast({
        title: 'Login failed',
        description: message,
        variant: 'destructive',
      })
    },
  })

  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: () => {
      navigate('/login')
      toast({
        title: 'Registration successful',
        description: 'Please log in with your new account.',
      })
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError
        ? error.message
        : error instanceof Error
          ? error.message
          : 'Something went wrong'

      toast({
        title: 'Registration failed',
        description: message,
        variant: 'destructive',
      })
    },
  })

  const logout = () => {
    authApi.logout()
    queryClient.clear()
    navigate('/login')
    toast({
      title: 'Logged out',
      description: 'You have been logged out successfully.',
    })
  }

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    login: loginMutation.mutate,
    register: registerMutation.mutate,
    logout,
    isLoginLoading: loginMutation.isPending,
    isRegisterLoading: registerMutation.isPending,
  }
}
