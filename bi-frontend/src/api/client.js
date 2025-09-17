import axios from 'axios'
import toast from 'react-hot-toast'
import { STORAGE_KEYS, ERROR_MESSAGES } from '../utils/constants'

// Base API URL: prefer explicit env var, otherwise use relative '/api' so Vite proxy works in dev
const BASE_API = import.meta.env.VITE_API_BASE_URL || '/api'

// Create axios instance
const api = axios.create({
  baseURL: BASE_API,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token management
const tokenManager = {
  getAccessToken: () => {
    try {
      return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
    } catch {
      return null
    }
  },
  
  getRefreshToken: () => {
    try {
      return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)
    } catch {
      return null
    }
  },
  
  setTokens: (accessToken, refreshToken) => {
    try {
      if (accessToken) {
        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken)
      }
      if (refreshToken) {
        localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken)
      }
    } catch (error) {
      console.error('Failed to store tokens:', error)
    }
  },
  
  clearTokens: () => {
    try {
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
      localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
      localStorage.removeItem(STORAGE_KEYS.USER_PROFILE)
    } catch (error) {
      console.error('Failed to clear tokens:', error)
    }
  },
}

// Request interceptor - Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = tokenManager.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - Handle auth errors and token refresh
api.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      const refreshToken = tokenManager.getRefreshToken()
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${BASE_API.replace(/\/$/, '')}/auth/refresh/`,
            { refresh: refreshToken }
          )
          
          const { access } = response.data
          tokenManager.setTokens(access, refreshToken)
          
          // Retry original request
          originalRequest.headers.Authorization = `Bearer ${access}`
          return api(originalRequest)
        } catch (refreshError) {
          // Refresh failed, redirect to login
          tokenManager.clearTokens()
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      } else {
        // No refresh token, redirect to login
        tokenManager.clearTokens()
        window.location.href = '/login'
      }
    }
    
    // Handle different error types
    const message = getErrorMessage(error)
    
    // Don't show toast for certain endpoints or methods
    const skipToast = 
      originalRequest.url?.includes('/auth/') ||
      originalRequest.method === 'get' ||
      originalRequest.skipErrorToast
    
    if (!skipToast) {
      toast.error(message)
    }
    
    return Promise.reject(error)
  }
)

// Get user-friendly error messages
function getErrorMessage(error) {
  if (error.response) {
    const status = error.response.status
    const data = error.response.data
    
    switch (status) {
      case 400:
        if (data.detail) return data.detail
        if (data.error) return data.error
        return ERROR_MESSAGES.VALIDATION_ERROR
      case 401:
        return ERROR_MESSAGES.UNAUTHORIZED
      case 403:
        return ERROR_MESSAGES.FORBIDDEN
      case 404:
        return ERROR_MESSAGES.NOT_FOUND
      case 500:
        return ERROR_MESSAGES.SERVER_ERROR
      default:
        return data.detail || data.error || ERROR_MESSAGES.SERVER_ERROR
    }
  } else if (error.request) {
    return ERROR_MESSAGES.NETWORK_ERROR
  } else {
    return error.message || ERROR_MESSAGES.SERVER_ERROR
  }
}

// Helper function to build query parameters
export function buildQueryParams(params) {
  const searchParams = new URLSearchParams()
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      if (Array.isArray(value)) {
        value.forEach(v => searchParams.append(key, v))
      } else if (value instanceof Date) {
        searchParams.append(key, value.toISOString().split('T')[0])
      } else {
        searchParams.append(key, value.toString())
      }
    }
  })
  
  return searchParams.toString()
}

// Helper function for paginated requests
export function buildPaginatedUrl(baseUrl, page, pageSize, filters = {}) {
  const params = {
    page,
    page_size: pageSize,
    ...filters,
  }
  
  const queryString = buildQueryParams(params)
  return queryString ? `${baseUrl}?${queryString}` : baseUrl
}

// Export api instance and token manager
export { api, tokenManager }
export const apiClient = api
export default api