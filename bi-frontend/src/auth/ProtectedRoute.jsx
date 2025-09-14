import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider'
import { USER_ROLES } from '../utils/constants'

/**
 * ProtectedRoute component that handles authentication and role-based access
 * 
 * @param {Object} props
 * @param {React.ReactNode} props.children - Child components to render if authorized
 * @param {string[]} [props.allowedRoles] - Array of roles allowed to access this route
 * @param {string} [props.redirectTo='/login'] - Where to redirect unauthorized users
 * @param {boolean} [props.requireAuth=true] - Whether authentication is required
 */
export default function ProtectedRoute({ 
  children, 
  allowedRoles = [], 
  redirectTo = '/login',
  requireAuth = true 
}) {
  const { isAuthenticated, user, isLoading } = useAuth()
  const location = useLocation()

  // Show loading while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  // If auth is required and user is not authenticated, redirect to login
  if (requireAuth && !isAuthenticated) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />
  }

  // If user is authenticated but doesn't have required role, show 403
  if (isAuthenticated && allowedRoles.length > 0 && !allowedRoles.includes(user?.role)) {
    return <Navigate to="/403" replace />
  }

  // If all checks pass, render children
  return children
}

/**
 * Component-level permission check
 * Only renders children if user has the required permission
 */
export function RequirePermission({ resource, action, children, fallback = null }) {
  const { hasPermission } = useAuth()

  if (!hasPermission(resource, action)) {
    return fallback
  }

  return children
}

/**
 * Role-based component rendering
 * Renders different content based on user role
 */
export function RoleBasedRender({ roles, children, fallback = null }) {
  const { user } = useAuth()

  if (!user || !roles[user.role]) {
    return fallback
  }

  return roles[user.role] || fallback
}

/**
 * Branch access guard
 * Only renders children if user can access the specified branch
 */
export function RequireBranchAccess({ branchId, children, fallback = null }) {
  const { canAccessBranch } = useAuth()

  if (!canAccessBranch(branchId)) {
    return fallback
  }

  return children
}

/**
 * Route guard for Super Admin only
 */
export function SuperAdminRoute({ children }) {
  return (
    <ProtectedRoute allowedRoles={[USER_ROLES.SUPER_ADMIN]}>
      {children}
    </ProtectedRoute>
  )
}

/**
 * Route guard for Manager and above
 */
export function ManagerRoute({ children }) {
  return (
    <ProtectedRoute allowedRoles={[USER_ROLES.SUPER_ADMIN, USER_ROLES.MANAGER]}>
      {children}
    </ProtectedRoute>
  )
}

/**
 * Route guard for Analyst and above  
 */
export function AnalystRoute({ children }) {
  return (
    <ProtectedRoute allowedRoles={[USER_ROLES.SUPER_ADMIN, USER_ROLES.MANAGER, USER_ROLES.ANALYST]}>
      {children}
    </ProtectedRoute>
  )
}