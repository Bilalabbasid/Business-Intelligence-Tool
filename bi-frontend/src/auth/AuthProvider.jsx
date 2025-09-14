import { createContext, useContext, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { authApi } from '../api/endpoints'
import { tokenManager } from '../api/client'
import { STORAGE_KEYS, ROLE_DASHBOARDS, QUERY_KEYS, SUCCESS_MESSAGES } from '../utils/constants'

const AuthContext = createContext({})

export function AuthProvider({ children }) {
  const [isInitialized, setIsInitialized] = useState(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Get user profile query
  const {
    data: user,
    isLoading,
    error,
    refetch: refetchProfile,
  } = useQuery({
    queryKey: QUERY_KEYS.USER_PROFILE,
    queryFn: async () => {
      const response = await authApi.getProfile()
      return response.data
    },
    enabled: !!tokenManager.getAccessToken(),
    retry: false,
    staleTime: 1000 * 60 * 30, // 30 minutes
  })

  // Initialize auth state
  useEffect(() => {
    const token = tokenManager.getAccessToken()
    if (token && !isLoading && !error) {
      setIsInitialized(true)
    } else if (!token) {
      setIsInitialized(true)
    } else if (error) {
      tokenManager.clearTokens()
      setIsInitialized(true)
    }
  }, [isLoading, error])

  const login = async (credentials) => {
    try {
      const response = await authApi.login(credentials)
      const { access, refresh, user: userData } = response.data

      // Store tokens
      tokenManager.setTokens(access, refresh)
      
      // Store user profile
      localStorage.setItem(STORAGE_KEYS.USER_PROFILE, JSON.stringify(userData))

      // Invalidate and refetch user profile
      queryClient.setQueryData(QUERY_KEYS.USER_PROFILE, userData)
      
      toast.success(SUCCESS_MESSAGES.LOGIN)

      // Navigate to role-specific dashboard
      const dashboardRoute = ROLE_DASHBOARDS[userData.role] || '/dashboard'
      navigate(dashboardRoute, { replace: true })

      return { success: true, user: userData }
    } catch (error) {
      console.error('Login error:', error)
      const message = error.response?.data?.detail || 'Login failed. Please check your credentials.'
      return { success: false, error: message }
    }
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // Clear tokens and user data
      tokenManager.clearTokens()
      queryClient.clear()
      toast.success(SUCCESS_MESSAGES.LOGOUT)
      navigate('/login', { replace: true })
    }
  }

  const register = async (userData) => {
    try {
      const response = await authApi.register(userData)
      toast.success('Registration successful! Please log in.')
      return { success: true, data: response.data }
    } catch (error) {
      console.error('Registration error:', error)
      const message = error.response?.data?.detail || 'Registration failed. Please try again.'
      return { success: false, error: message }
    }
  }

  const hasPermission = (resource, action) => {
    if (!user) return false
    
    // Super admin has all permissions
    if (user.role === 'SUPER_ADMIN') return true
    
    // Check role-specific permissions
    const rolePermissions = {
      MANAGER: {
        branches: ['read', 'update'],
        sales: ['create', 'read', 'update', 'delete'],
        inventory: ['create', 'read', 'update', 'delete'],
        customers: ['create', 'read', 'update', 'delete'],
        staff: ['create', 'read', 'update', 'delete'],
        analytics: ['read'],
        audit: ['read'],
      },
      ANALYST: {
        branches: ['read'],
        sales: ['read'],
        inventory: ['read'],
        customers: ['read'],
        staff: ['read'],
        analytics: ['read'],
        audit: ['read'],
      },
      STAFF: {
        branches: ['read'],
        sales: ['create', 'read'],
        inventory: ['read', 'update'],
        customers: ['create', 'read', 'update'],
        staff: ['read'],
        analytics: [],
        audit: [],
      },
    }

    const permissions = rolePermissions[user.role] || {}
    const resourcePermissions = permissions[resource] || []
    return resourcePermissions.includes(action)
  }

  const canAccessBranch = (branchId) => {
    if (!user) return false
    if (user.role === 'SUPER_ADMIN') return true
    return user.branch_id === branchId
  }

  const value = {
    user,
    isLoading: isLoading && !isInitialized,
    isAuthenticated: !!user && !!tokenManager.getAccessToken(),
    login,
    logout,
    register,
    hasPermission,
    canAccessBranch,
    refetchProfile,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}