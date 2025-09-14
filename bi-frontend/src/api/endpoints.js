import api, { buildQueryParams, buildPaginatedUrl } from './client'
import { API_ENDPOINTS } from '../utils/constants'

// Authentication API
export const authApi = {
  login: (credentials) => 
    api.post(API_ENDPOINTS.AUTH.LOGIN, credentials),
  
  logout: () => 
    api.post(API_ENDPOINTS.AUTH.LOGOUT),
  
  refresh: (refreshToken) => 
    api.post(API_ENDPOINTS.AUTH.REFRESH, { refresh: refreshToken }),
  
  getProfile: () => 
    api.get(API_ENDPOINTS.AUTH.PROFILE),
  
  register: (userData) => 
    api.post(API_ENDPOINTS.AUTH.REGISTER, userData),
}

// Branches API
export const branchesApi = {
  list: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = queryString ? `${API_ENDPOINTS.BRANCHES}?${queryString}` : API_ENDPOINTS.BRANCHES
    return api.get(url)
  },
  
  get: (id) => 
    api.get(`${API_ENDPOINTS.BRANCHES}${id}/`),
  
  create: (branchData) => 
    api.post(API_ENDPOINTS.BRANCHES, branchData),
  
  update: (id, branchData) => 
    api.put(`${API_ENDPOINTS.BRANCHES}${id}/`, branchData),
  
  patch: (id, branchData) => 
    api.patch(`${API_ENDPOINTS.BRANCHES}${id}/`, branchData),
  
  delete: (id) => 
    api.delete(`${API_ENDPOINTS.BRANCHES}${id}/`),
  
  getPerformanceSummary: (id, filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = `${API_ENDPOINTS.BRANCHES}${id}/performance_summary/`
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
}

// Sales API
export const salesApi = {
  list: (page = 1, pageSize = 25, filters = {}) => {
    const url = buildPaginatedUrl(API_ENDPOINTS.SALES, page, pageSize, filters)
    return api.get(url)
  },
  
  get: (id) => 
    api.get(`${API_ENDPOINTS.SALES}${id}/`),
  
  create: (salesData) => 
    api.post(API_ENDPOINTS.SALES, salesData),
  
  update: (id, salesData) => 
    api.put(`${API_ENDPOINTS.SALES}${id}/`, salesData),
  
  patch: (id, salesData) => 
    api.patch(`${API_ENDPOINTS.SALES}${id}/`, salesData),
  
  delete: (id) => 
    api.delete(`${API_ENDPOINTS.SALES}${id}/`),
  
  getDailySummary: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = `${API_ENDPOINTS.SALES}daily_summary/`
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
  
  getRevenueTrends: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = `${API_ENDPOINTS.SALES}revenue_trends/`
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
}

// Inventory API
export const inventoryApi = {
  list: (page = 1, pageSize = 25, filters = {}) => {
    const url = buildPaginatedUrl(API_ENDPOINTS.INVENTORY, page, pageSize, filters)
    return api.get(url)
  },
  
  get: (id) => 
    api.get(`${API_ENDPOINTS.INVENTORY}${id}/`),
  
  create: (inventoryData) => 
    api.post(API_ENDPOINTS.INVENTORY, inventoryData),
  
  update: (id, inventoryData) => 
    api.put(`${API_ENDPOINTS.INVENTORY}${id}/`, inventoryData),
  
  patch: (id, inventoryData) => 
    api.patch(`${API_ENDPOINTS.INVENTORY}${id}/`, inventoryData),
  
  delete: (id) => 
    api.delete(`${API_ENDPOINTS.INVENTORY}${id}/`),
  
  getLowStockAlert: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = `${API_ENDPOINTS.INVENTORY}low_stock_alert/`
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
  
  getExpiryAlert: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = `${API_ENDPOINTS.INVENTORY}expiry_alert/`
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
  
  bulkUpdateStock: (updates) => 
    api.post(`${API_ENDPOINTS.INVENTORY}bulk_update_stock/`, { updates }),
}

// Customers API
export const customersApi = {
  list: (page = 1, pageSize = 25, filters = {}) => {
    const url = buildPaginatedUrl(API_ENDPOINTS.CUSTOMERS, page, pageSize, filters)
    return api.get(url)
  },
  
  get: (id) => 
    api.get(`${API_ENDPOINTS.CUSTOMERS}${id}/`),
  
  create: (customerData) => 
    api.post(API_ENDPOINTS.CUSTOMERS, customerData),
  
  update: (id, customerData) => 
    api.put(`${API_ENDPOINTS.CUSTOMERS}${id}/`, customerData),
  
  patch: (id, customerData) => 
    api.patch(`${API_ENDPOINTS.CUSTOMERS}${id}/`, customerData),
  
  delete: (id) => 
    api.delete(`${API_ENDPOINTS.CUSTOMERS}${id}/`),
  
  getLoyaltyTiers: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = `${API_ENDPOINTS.CUSTOMERS}loyalty_tiers/`
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
}

// Staff Performance API
export const staffPerformanceApi = {
  list: (page = 1, pageSize = 25, filters = {}) => {
    const url = buildPaginatedUrl(API_ENDPOINTS.STAFF_PERFORMANCE, page, pageSize, filters)
    return api.get(url)
  },
  
  get: (id) => 
    api.get(`${API_ENDPOINTS.STAFF_PERFORMANCE}${id}/`),
  
  create: (performanceData) => 
    api.post(API_ENDPOINTS.STAFF_PERFORMANCE, performanceData),
  
  update: (id, performanceData) => 
    api.put(`${API_ENDPOINTS.STAFF_PERFORMANCE}${id}/`, performanceData),
  
  patch: (id, performanceData) => 
    api.patch(`${API_ENDPOINTS.STAFF_PERFORMANCE}${id}/`, performanceData),
  
  delete: (id) => 
    api.delete(`${API_ENDPOINTS.STAFF_PERFORMANCE}${id}/`),
  
  getPerformanceRankings: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = `${API_ENDPOINTS.STAFF_PERFORMANCE}performance_rankings/`
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
}

// Audit Logs API
export const auditLogsApi = {
  list: (page = 1, pageSize = 50, filters = {}) => {
    const url = buildPaginatedUrl(API_ENDPOINTS.AUDIT_LOGS, page, pageSize, filters)
    return api.get(url)
  },
  
  get: (id) => 
    api.get(`${API_ENDPOINTS.AUDIT_LOGS}${id}/`),
  
  getActivitySummary: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = `${API_ENDPOINTS.AUDIT_LOGS}activity_summary/`
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
}

// KPI API (custom endpoints for dashboard metrics)
export const kpiApi = {
  getDashboardMetrics: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = '/v1/kpis/dashboard/'
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
  
  getBranchComparison: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = '/v1/kpis/branch-comparison/'
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
  
  getAlertsSummary: (filters = {}) => {
    const queryString = buildQueryParams(filters)
    const url = '/v1/kpis/alerts/'
    return api.get(queryString ? `${url}?${queryString}` : url)
  },
}