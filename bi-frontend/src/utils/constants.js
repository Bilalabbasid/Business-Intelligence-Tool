// User roles
export const USER_ROLES = {
  SUPER_ADMIN: 'SUPER_ADMIN',
  MANAGER: 'MANAGER',
  ANALYST: 'ANALYST',
  STAFF: 'STAFF',
}

// Role labels for display
export const ROLE_LABELS = {
  [USER_ROLES.SUPER_ADMIN]: 'Super Admin',
  [USER_ROLES.MANAGER]: 'Manager',
  [USER_ROLES.ANALYST]: 'Analyst',
  [USER_ROLES.STAFF]: 'Staff',
}

// Role permissions
export const ROLE_PERMISSIONS = {
  [USER_ROLES.SUPER_ADMIN]: {
    branches: ['create', 'read', 'update', 'delete'],
    sales: ['create', 'read', 'update', 'delete'],
    inventory: ['create', 'read', 'update', 'delete'],
    customers: ['create', 'read', 'update', 'delete'],
    staff: ['create', 'read', 'update', 'delete'],
    analytics: ['read'],
    audit: ['read'],
  },
  [USER_ROLES.MANAGER]: {
    branches: ['read', 'update'],
    sales: ['create', 'read', 'update', 'delete'],
    inventory: ['create', 'read', 'update', 'delete'],
    customers: ['create', 'read', 'update', 'delete'],
    staff: ['create', 'read', 'update', 'delete'],
    analytics: ['read'],
    audit: ['read'],
  },
  [USER_ROLES.ANALYST]: {
    branches: ['read'],
    sales: ['read'],
    inventory: ['read'],
    customers: ['read'],
    staff: ['read'],
    analytics: ['read'],
    audit: ['read'],
  },
  [USER_ROLES.STAFF]: {
    branches: ['read'],
    sales: ['create', 'read'],
    inventory: ['read', 'update'],
    customers: ['create', 'read', 'update'],
    staff: ['read'],
    analytics: [],
    audit: [],
  },
}

// Dashboard routes by role
export const ROLE_DASHBOARDS = {
  [USER_ROLES.SUPER_ADMIN]: '/dashboard/super',
  [USER_ROLES.MANAGER]: '/dashboard/branch',
  [USER_ROLES.ANALYST]: '/dashboard/analyst',
  [USER_ROLES.STAFF]: '/dashboard/staff',
}

// Payment methods
export const PAYMENT_METHODS = {
  CASH: 'CASH',
  CARD: 'CARD',
  ONLINE: 'ONLINE',
}

// Order types
export const ORDER_TYPES = {
  DINE_IN: 'DINE_IN',
  TAKEOUT: 'TAKEOUT',
  DELIVERY: 'DELIVERY',
}

// Status types
export const STATUS_TYPES = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  PENDING: 'pending',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
}

// Customer loyalty tiers
export const LOYALTY_TIERS = {
  BRONZE: 'Bronze',
  SILVER: 'Silver',
  GOLD: 'Gold',
  PLATINUM: 'Platinum',
}

// Date range presets
export const DATE_RANGE_PRESETS = [
  {
    label: 'Today',
    value: 'today',
    getDates: () => {
      const today = new Date()
      return {
        start: new Date(today.setHours(0, 0, 0, 0)),
        end: new Date(today.setHours(23, 59, 59, 999))
      }
    }
  },
  {
    label: 'Yesterday',
    value: 'yesterday',
    getDates: () => {
      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - 1)
      return {
        start: new Date(yesterday.setHours(0, 0, 0, 0)),
        end: new Date(yesterday.setHours(23, 59, 59, 999))
      }
    }
  },
  {
    label: 'Last 7 days',
    value: '7days',
    getDates: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 6)
      return {
        start: new Date(start.setHours(0, 0, 0, 0)),
        end: new Date(end.setHours(23, 59, 59, 999))
      }
    }
  },
  {
    label: 'Last 30 days',
    value: '30days',
    getDates: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 29)
      return {
        start: new Date(start.setHours(0, 0, 0, 0)),
        end: new Date(end.setHours(23, 59, 59, 999))
      }
    }
  },
  {
    label: 'This month',
    value: 'thisMonth',
    getDates: () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), now.getMonth(), 1)
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59, 999)
      return { start, end }
    }
  },
  {
    label: 'Last month',
    value: 'lastMonth',
    getDates: () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const end = new Date(now.getFullYear(), now.getMonth(), 0, 23, 59, 59, 999)
      return { start, end }
    }
  },
  {
    label: 'This year',
    value: 'thisYear',
    getDates: () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), 0, 1)
      const end = new Date(now.getFullYear(), 11, 31, 23, 59, 59, 999)
      return { start, end }
    }
  }
]

// Chart colors
export const CHART_COLORS = [
  '#3B82F6', // blue
  '#10B981', // emerald
  '#F59E0B', // amber
  '#EF4444', // red
  '#8B5CF6', // violet
  '#F97316', // orange
  '#06B6D4', // cyan
  '#84CC16', // lime
  '#EC4899', // pink
  '#6B7280', // gray
]

// API endpoints
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login/',
    LOGOUT: '/auth/logout/',
    REFRESH: '/auth/refresh/',
    REGISTER: '/auth/register/',
    PROFILE: '/auth/profile/',
  },
  BRANCHES: '/v1/branches/',
  SALES: '/v1/sales/',
  INVENTORY: '/v1/inventory/',
  CUSTOMERS: '/v1/customers/',
  STAFF_PERFORMANCE: '/v1/staff-performance/',
  AUDIT_LOGS: '/v1/audit-logs/',
}

// Local storage keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'bi_access_token',
  REFRESH_TOKEN: 'bi_refresh_token',
  USER_PROFILE: 'bi_user_profile',
  THEME: 'bi_theme',
  SIDEBAR_COLLAPSED: 'bi_sidebar_collapsed',
}

// Query keys for React Query
export const QUERY_KEYS = {
  USER_PROFILE: ['user', 'profile'],
  BRANCHES: ['branches'],
  BRANCH_DETAIL: (id) => ['branches', id],
  BRANCH_PERFORMANCE: (id, filters) => ['branches', id, 'performance', filters],
  SALES: (filters) => ['sales', filters],
  SALES_SUMMARY: (filters) => ['sales', 'summary', filters],
  SALES_TRENDS: (filters) => ['sales', 'trends', filters],
  INVENTORY: (filters) => ['inventory', filters],
  INVENTORY_ALERTS: (filters) => ['inventory', 'alerts', filters],
  CUSTOMERS: (filters) => ['customers', filters],
  CUSTOMER_LOYALTY: (filters) => ['customers', 'loyalty', filters],
  STAFF_PERFORMANCE: (filters) => ['staff-performance', filters],
  STAFF_RANKINGS: (filters) => ['staff-performance', 'rankings', filters],
  AUDIT_LOGS: (filters) => ['audit-logs', filters],
  KPI_DATA: (filters) => ['kpi', filters],
}

// Error messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  FORBIDDEN: 'Access denied. Please contact your administrator.',
  NOT_FOUND: 'The requested resource was not found.',
  SERVER_ERROR: 'Server error. Please try again later.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  SESSION_EXPIRED: 'Your session has expired. Please log in again.',
}

// Success messages
export const SUCCESS_MESSAGES = {
  LOGIN: 'Welcome back!',
  LOGOUT: 'You have been logged out successfully.',
  SAVE: 'Changes saved successfully.',
  DELETE: 'Item deleted successfully.',
  CREATE: 'Item created successfully.',
  UPDATE: 'Item updated successfully.',
  EXPORT: 'Data exported successfully.',
}