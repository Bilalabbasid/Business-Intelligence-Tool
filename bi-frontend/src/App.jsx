import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthProvider'
import ProtectedRoute from './auth/ProtectedRoute'
import Layout from './components/layout/Layout'
import Login from './pages/auth/Login'
import SuperAdminDashboard from './pages/dashboard/SuperAdminDashboard'
import BranchManagerDashboard from './pages/dashboard/BranchManagerDashboard'
import AnalystDashboard from './pages/dashboard/AnalystDashboard'
import StaffDashboard from './pages/dashboard/StaffDashboard'
import SalesList from './pages/sales/SalesList'
import InventoryList from './pages/inventory/InventoryList'
import CustomersList from './pages/customers/CustomersList'
import { USER_ROLES } from './utils/constants'
import './App.css'

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="App">
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/403" element={<ForbiddenPage />} />
            <Route path="/404" element={<NotFoundPage />} />
            
            {/* Protected Routes with Layout */}
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Routes>
                      {/* Dashboard Routes */}
                      <Route path="/dashboard/super" element={
                        <ProtectedRoute allowedRoles={[USER_ROLES.SUPER_ADMIN]}>
                          <SuperAdminDashboard />
                        </ProtectedRoute>
                      } />
                      
                      <Route path="/dashboard/branch" element={
                        <ProtectedRoute allowedRoles={[USER_ROLES.MANAGER]}>
                          <BranchManagerDashboard />
                        </ProtectedRoute>
                      } />
                      
                      <Route path="/dashboard/analyst" element={
                        <ProtectedRoute allowedRoles={[USER_ROLES.ANALYST]}>
                          <AnalystDashboard />
                        </ProtectedRoute>
                      } />
                      
                      <Route path="/dashboard/staff" element={
                        <ProtectedRoute allowedRoles={[USER_ROLES.STAFF]}>
                          <StaffDashboard />
                        </ProtectedRoute>
                      } />
                      
                      {/* Data Management Routes */}
                      <Route path="/sales" element={<SalesList />} />
                      <Route path="/inventory" element={<InventoryList />} />
                      <Route path="/customers" element={<CustomersList />} />
                      
                      {/* Default redirect based on role */}
                      <Route path="/" element={<RoleBasedRedirect />} />
                      <Route path="/dashboard" element={<RoleBasedRedirect />} />
                      
                      {/* Catch all - 404 */}
                      <Route path="*" element={<Navigate to="/404" replace />} />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </AuthProvider>
    </Router>
  )
}

// Role-based redirect component
function RoleBasedRedirect() {
  const { user } = useAuth()
  
  if (!user) return <Navigate to="/login" replace />
  
  const dashboardRoutes = {
    [USER_ROLES.SUPER_ADMIN]: '/dashboard/super',
    [USER_ROLES.MANAGER]: '/dashboard/branch',
    [USER_ROLES.ANALYST]: '/dashboard/analyst',
    [USER_ROLES.STAFF]: '/dashboard/staff',
  }
  
  const route = dashboardRoutes[user.role] || '/dashboard/staff'
  return <Navigate to={route} replace />
}

// 403 Forbidden Page
function ForbiddenPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-400">403</h1>
        <p className="text-xl text-gray-600 dark:text-gray-400 mt-4">Access Forbidden</p>
        <p className="text-gray-500 dark:text-gray-500 mt-2">
          You don't have permission to access this resource.
        </p>
        <div className="mt-6">
          <button
            onClick={() => window.history.back()}
            className="btn btn-primary"
          >
            Go Back
          </button>
        </div>
      </div>
    </div>
  )
}

// 404 Not Found Page
function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-400">404</h1>
        <p className="text-xl text-gray-600 dark:text-gray-400 mt-4">Page Not Found</p>
        <p className="text-gray-500 dark:text-gray-500 mt-2">
          The page you're looking for doesn't exist.
        </p>
        <div className="mt-6">
          <Link to="/dashboard" className="btn btn-primary">
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}

export default App