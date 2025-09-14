import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  ShoppingCart,
  Package,
  Users,
  BarChart3,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu
} from 'lucide-react'
import { useAuth } from '../../auth/AuthProvider'
import { USER_ROLES } from '../../utils/constants'
import { cn } from '../../utils'

export default function Sidebar({ isOpen, isCollapsed, onClose, onToggleCollapsed }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  // Navigation items based on user role
  const getNavigationItems = () => {
    const baseItems = [
      {
        name: 'Dashboard',
        href: getDashboardRoute(user?.role),
        icon: LayoutDashboard,
        current: location.pathname.includes('/dashboard')
      }
    ]

    const roleBasedItems = {
      [USER_ROLES.SUPER_ADMIN]: [
        { name: 'Branches', href: '/branches', icon: Building2 },
        { name: 'Sales', href: '/sales', icon: ShoppingCart },
        { name: 'Inventory', href: '/inventory', icon: Package },
        { name: 'Customers', href: '/customers', icon: Users },
        { name: 'Analytics', href: '/analytics', icon: BarChart3 },
      ],
      [USER_ROLES.MANAGER]: [
        { name: 'Sales', href: '/sales', icon: ShoppingCart },
        { name: 'Inventory', href: '/inventory', icon: Package },
        { name: 'Customers', href: '/customers', icon: Users },
        { name: 'Staff', href: '/staff', icon: Users },
        { name: 'Reports', href: '/reports', icon: BarChart3 },
      ],
      [USER_ROLES.ANALYST]: [
        { name: 'Sales', href: '/sales', icon: ShoppingCart },
        { name: 'Inventory', href: '/inventory', icon: Package },
        { name: 'Customers', href: '/customers', icon: Users },
        { name: 'Analytics', href: '/analytics', icon: BarChart3 },
      ],
      [USER_ROLES.STAFF]: [
        { name: 'Sales', href: '/sales', icon: ShoppingCart },
        { name: 'Inventory', href: '/inventory', icon: Package },
        { name: 'Customers', href: '/customers', icon: Users },
      ]
    }

    const additionalItems = roleBasedItems[user?.role] || []
    
    return [
      ...baseItems,
      ...additionalItems.map(item => ({
        ...item,
        current: location.pathname.includes(item.href)
      }))
    ]
  }

  const handleLogout = async () => {
    await logout()
  }

  const navigationItems = getNavigationItems()

  return (
    <>
      {/* Desktop sidebar */}
      <div 
        className={cn(
          'fixed inset-y-0 left-0 z-50 bg-white dark:bg-gray-800 shadow-lg transition-all duration-300',
          'hidden lg:flex lg:flex-col',
          isCollapsed ? 'w-16' : 'w-64'
        )}
      >
        {/* Logo and brand */}
        <div className={cn(
          'flex items-center justify-between px-4 py-4 border-b border-gray-200 dark:border-gray-700',
          isCollapsed && 'px-2 justify-center'
        )}>
          {!isCollapsed ? (
            <>
              <div className="flex items-center space-x-3">
                <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
                  <Building2 className="h-5 w-5 text-white" />
                </div>
                <span className="text-lg font-semibold text-gray-900 dark:text-white">
                  BI Tool
                </span>
              </div>
              <button
                onClick={onToggleCollapsed}
                className="p-1 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 dark:hover:text-gray-300"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            </>
          ) : (
            <button
              onClick={onToggleCollapsed}
              className="p-1 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 dark:hover:text-gray-300"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* User info */}
        {!isCollapsed && user && (
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-3">
              <div className="h-8 w-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                  {user.first_name?.[0] || user.username?.[0] || 'U'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user.username}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user.role?.replace('_', ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navigationItems.map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'sidebar-item',
                  item.current && 'active',
                  isCollapsed && 'justify-center px-2'
                )}
                title={isCollapsed ? item.name : ''}
              >
                <Icon className={cn('h-5 w-5 flex-shrink-0', isCollapsed && 'h-6 w-6')} />
                {!isCollapsed && (
                  <span className="text-sm font-medium">{item.name}</span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Settings and Logout */}
        <div className="px-4 py-4 border-t border-gray-200 dark:border-gray-700 space-y-1">
          <Link
            to="/settings"
            className={cn(
              'sidebar-item',
              location.pathname.includes('/settings') && 'active',
              isCollapsed && 'justify-center px-2'
            )}
            title={isCollapsed ? 'Settings' : ''}
          >
            <Settings className={cn('h-5 w-5 flex-shrink-0', isCollapsed && 'h-6 w-6')} />
            {!isCollapsed && (
              <span className="text-sm font-medium">Settings</span>
            )}
          </Link>
          
          <button
            onClick={handleLogout}
            className={cn(
              'sidebar-item w-full text-left text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:text-red-300 dark:hover:bg-red-900/20',
              isCollapsed && 'justify-center px-2'
            )}
            title={isCollapsed ? 'Sign Out' : ''}
          >
            <LogOut className={cn('h-5 w-5 flex-shrink-0', isCollapsed && 'h-6 w-6')} />
            {!isCollapsed && (
              <span className="text-sm font-medium">Sign Out</span>
            )}
          </button>
        </div>
      </div>

      {/* Mobile sidebar */}
      <div 
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 shadow-lg transform transition-transform duration-300 lg:hidden',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Mobile logo and close button */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Building2 className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              BI Tool
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 dark:hover:text-gray-300"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
        </div>

        {/* Mobile user info */}
        {user && (
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-3">
              <div className="h-8 w-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                  {user.first_name?.[0] || user.username?.[0] || 'U'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user.username}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user.role?.replace('_', ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Mobile navigation */}
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navigationItems.map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={onClose}
                className={cn(
                  'sidebar-item',
                  item.current && 'active'
                )}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm font-medium">{item.name}</span>
              </Link>
            )
          })}
        </nav>

        {/* Mobile settings and logout */}
        <div className="px-4 py-4 border-t border-gray-200 dark:border-gray-700 space-y-1">
          <Link
            to="/settings"
            onClick={onClose}
            className={cn(
              'sidebar-item',
              location.pathname.includes('/settings') && 'active'
            )}
          >
            <Settings className="h-5 w-5 flex-shrink-0" />
            <span className="text-sm font-medium">Settings</span>
          </Link>
          
          <button
            onClick={handleLogout}
            className="sidebar-item w-full text-left text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:text-red-300 dark:hover:bg-red-900/20"
          >
            <LogOut className="h-5 w-5 flex-shrink-0" />
            <span className="text-sm font-medium">Sign Out</span>
          </button>
        </div>
      </div>
    </>
  )
}

function getDashboardRoute(role) {
  const routes = {
    [USER_ROLES.SUPER_ADMIN]: '/dashboard/super',
    [USER_ROLES.MANAGER]: '/dashboard/branch',
    [USER_ROLES.ANALYST]: '/dashboard/analyst',
    [USER_ROLES.STAFF]: '/dashboard/staff',
  }
  return routes[role] || '/dashboard'
}