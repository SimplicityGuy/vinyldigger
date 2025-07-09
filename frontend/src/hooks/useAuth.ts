import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/lib/api'
import { useToast } from './useToast'

export function useAuth() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { toast } = useToast()

  const { data: user, isLoading } = useQuery({
    queryKey: ['user'],
    queryFn: authApi.getMe,
    retry: false,
    enabled: !!localStorage.getItem('access_token'),
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
    onError: (error: any) => {
      toast({
        title: 'Login failed',
        description: error.message || 'Invalid credentials',
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
    onError: (error: any) => {
      toast({
        title: 'Registration failed',
        description: error.message || 'Something went wrong',
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