/**
 * ChartControls Component
 * Date range picker, aggregation toggles, and export controls for charts
 */

import React, { useState, useCallback, useMemo } from 'react'
import { 
  Calendar, 
  Download, 
  Filter, 
  RefreshCw, 
  Settings,
  Building2,
  ChevronDown,
  X
} from 'lucide-react'
import { Menu, Transition } from '@headlessui/react'
import { cn } from '../utils'
import { useAuth } from '../auth/AuthProvider'
import { exportMultipleFormats, generatePermalink, copyToClipboard } from './exportUtils'
import { formatDate } from './chartUtils'
import { USER_ROLES } from '../utils/constants'

/**
 * ChartControls Component
 * @param {Object} props - Component props
 * @param {Object} props.filters - Current filter values
 * @param {Function} props.onFiltersChange - Filter change handler
 * @param {Array} props.branches - Available branches for Super Admin
 * @param {Array} props.data - Chart data for export
 * @param {Array} props.exportColumns - Columns for CSV export
 * @param {string} props.exportId - Chart element ID for image export
 * @param {Function} props.onRefresh - Refresh data handler
 * @param {boolean} props.isLoading - Loading state
 * @param {string} props.className - CSS class name
 */
export default function ChartControls({
  filters = {},
  onFiltersChange = () => {},
  branches = [],
  data = [],
  exportColumns = [],
  exportId = 'chart',
  onRefresh = () => {},
  isLoading = false,
  className = ''
}) {
  const { user } = useAuth()
  const [showFilters, setShowFilters] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  // Date range presets
  const datePresets = useMemo(() => [
    {
      label: 'Last 7 days',
      value: 'last_7_days',
      startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      endDate: new Date()
    },
    {
      label: 'Last 30 days',
      value: 'last_30_days',
      startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      endDate: new Date()
    },
    {
      label: 'Last 90 days',
      value: 'last_90_days',
      startDate: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000),
      endDate: new Date()
    },
    {
      label: 'This month',
      value: 'this_month',
      startDate: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
      endDate: new Date()
    },
    {
      label: 'Last month',
      value: 'last_month',
      startDate: new Date(new Date().getFullYear(), new Date().getMonth() - 1, 1),
      endDate: new Date(new Date().getFullYear(), new Date().getMonth(), 0)
    },
    {
      label: 'This year',
      value: 'this_year',
      startDate: new Date(new Date().getFullYear(), 0, 1),
      endDate: new Date()
    }
  ], [])

  // Aggregation options
  const aggregationOptions = useMemo(() => [
    { label: 'Raw Data', value: 'raw' },
    { label: 'Hourly', value: 'hour' },
    { label: 'Daily', value: 'day' },
    { label: 'Weekly', value: 'week' },
    { label: 'Monthly', value: 'month' }
  ], [])

  // Handle date preset selection
  const handleDatePreset = useCallback((preset) => {
    onFiltersChange({
      ...filters,
      startDate: preset.startDate.toISOString().split('T')[0],
      endDate: preset.endDate.toISOString().split('T')[0],
      datePreset: preset.value
    })
  }, [filters, onFiltersChange])

  // Handle custom date change
  const handleDateChange = useCallback((field, value) => {
    onFiltersChange({
      ...filters,
      [field]: value,
      datePreset: 'custom'
    })
  }, [filters, onFiltersChange])

  // Handle aggregation change
  const handleAggregationChange = useCallback((aggregation) => {
    onFiltersChange({
      ...filters,
      aggregation
    })
  }, [filters, onFiltersChange])

  // Handle branch selection (Super Admin only)
  const handleBranchChange = useCallback((branchIds) => {
    onFiltersChange({
      ...filters,
      branchIds: Array.isArray(branchIds) ? branchIds : [branchIds]
    })
  }, [filters, onFiltersChange])

  // Handle export
  const handleExport = useCallback(async (formats = ['png', 'csv']) => {
    if (!exportId && !data.length) return

    setIsExporting(true)
    try {
      const results = await exportMultipleFormats(
        exportId,
        data,
        exportColumns,
        `chart_${Date.now()}`,
        formats
      )

      const successful = results.filter(r => r.success).length
      const failed = results.filter(r => !r.success).length

      // Show notification (implement with your toast system)
      console.log(`Export completed: ${successful} successful, ${failed} failed`)
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setIsExporting(false)
    }
  }, [exportId, data, exportColumns])

  // Handle share permalink
  const handleShare = useCallback(async () => {
    const config = {
      filters,
      timestamp: Date.now()
    }

    const result = generatePermalink(config)
    if (result.success) {
      const copied = await copyToClipboard(result.permalink)
      if (copied.success) {
        console.log('Permalink copied to clipboard')
      }
    }
  }, [filters])

  // Reset filters
  const handleResetFilters = useCallback(() => {
    onFiltersChange({
      startDate: '',
      endDate: '',
      aggregation: 'day',
      branchIds: [],
      datePreset: ''
    })
  }, [onFiltersChange])

  // Check if Super Admin can see branch selector
  const canSelectBranches = user?.role === USER_ROLES.SUPER_ADMIN && branches.length > 0

  return (
    <div className={cn('flex flex-wrap items-center gap-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg', className)}>
      {/* Date Range Controls */}
      <div className="flex items-center space-x-2">
        <Calendar className="h-4 w-4 text-gray-500" />
        <Menu as="div" className="relative">
          <Menu.Button className="flex items-center space-x-1 px-3 py-1 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600">
            <span className="text-gray-700 dark:text-gray-300">
              {filters.datePreset ? 
                datePresets.find(p => p.value === filters.datePreset)?.label || 'Custom Range'
                : 'Date Range'
              }
            </span>
            <ChevronDown className="h-3 w-3 text-gray-500" />
          </Menu.Button>
          
          <Transition
            enter="transition ease-out duration-100"
            enterFrom="transform opacity-0 scale-95"
            enterTo="transform opacity-100 scale-100"
            leave="transition ease-in duration-75"
            leaveFrom="transform opacity-100 scale-100"
            leaveTo="transform opacity-0 scale-95"
          >
            <Menu.Items className="absolute left-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
              <div className="p-3">
                <div className="space-y-2">
                  {datePresets.map(preset => (
                    <Menu.Item key={preset.value}>
                      {({ active }) => (
                        <button
                          onClick={() => handleDatePreset(preset)}
                          className={cn(
                            'w-full text-left px-2 py-1 text-sm rounded',
                            active && 'bg-gray-100 dark:bg-gray-700',
                            filters.datePreset === preset.value && 'text-primary-600 dark:text-primary-400 font-medium'
                          )}
                        >
                          {preset.label}
                        </button>
                      )}
                    </Menu.Item>
                  ))}
                  
                  <div className="border-t border-gray-200 dark:border-gray-600 pt-2 mt-2">
                    <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Custom Range</div>
                    <div className="space-y-2">
                      <input
                        type="date"
                        value={filters.startDate || ''}
                        onChange={(e) => handleDateChange('startDate', e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
                        placeholder="Start Date"
                      />
                      <input
                        type="date"
                        value={filters.endDate || ''}
                        onChange={(e) => handleDateChange('endDate', e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
                        placeholder="End Date"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </Menu.Items>
          </Transition>
        </Menu>
      </div>

      {/* Aggregation Control */}
      <Menu as="div" className="relative">
        <Menu.Button className="flex items-center space-x-1 px-3 py-1 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600">
          <span className="text-gray-700 dark:text-gray-300">
            {aggregationOptions.find(a => a.value === filters.aggregation)?.label || 'Daily'}
          </span>
          <ChevronDown className="h-3 w-3 text-gray-500" />
        </Menu.Button>
        
        <Transition
          enter="transition ease-out duration-100"
          enterFrom="transform opacity-0 scale-95"
          enterTo="transform opacity-100 scale-100"
          leave="transition ease-in duration-75"
          leaveFrom="transform opacity-100 scale-100"
          leaveTo="transform opacity-0 scale-95"
        >
          <Menu.Items className="absolute left-0 mt-2 w-32 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
            <div className="py-1">
              {aggregationOptions.map(option => (
                <Menu.Item key={option.value}>
                  {({ active }) => (
                    <button
                      onClick={() => handleAggregationChange(option.value)}
                      className={cn(
                        'w-full text-left px-3 py-2 text-sm',
                        active && 'bg-gray-100 dark:bg-gray-700',
                        filters.aggregation === option.value && 'text-primary-600 dark:text-primary-400 font-medium'
                      )}
                    >
                      {option.label}
                    </button>
                  )}
                </Menu.Item>
              ))}
            </div>
          </Menu.Items>
        </Transition>
      </Menu>

      {/* Branch Selector (Super Admin only) */}
      {canSelectBranches && (
        <Menu as="div" className="relative">
          <Menu.Button className="flex items-center space-x-1 px-3 py-1 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600">
            <Building2 className="h-3 w-3 text-gray-500" />
            <span className="text-gray-700 dark:text-gray-300">
              {filters.branchIds?.length > 0 ? 
                `${filters.branchIds.length} branch${filters.branchIds.length > 1 ? 'es' : ''}`
                : 'All Branches'
              }
            </span>
            <ChevronDown className="h-3 w-3 text-gray-500" />
          </Menu.Button>
          
          <Transition
            enter="transition ease-out duration-100"
            enterFrom="transform opacity-0 scale-95"
            enterTo="transform opacity-100 scale-100"
            leave="transition ease-in duration-75"
            leaveFrom="transform opacity-100 scale-100"
            leaveTo="transform opacity-0 scale-95"
          >
            <Menu.Items className="absolute left-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50 max-h-64 overflow-y-auto">
              <div className="p-3">
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Select Branches</div>
                <div className="space-y-1">
                  {branches.map(branch => (
                    <label key={branch.id} className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 p-1 rounded">
                      <input
                        type="checkbox"
                        checked={filters.branchIds?.includes(branch.id) || false}
                        onChange={(e) => {
                          const currentIds = filters.branchIds || []
                          const newIds = e.target.checked 
                            ? [...currentIds, branch.id]
                            : currentIds.filter(id => id !== branch.id)
                          handleBranchChange(newIds)
                        }}
                        className="rounded text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{branch.name}</span>
                    </label>
                  ))}
                </div>
              </div>
            </Menu.Items>
          </Transition>
        </Menu>
      )}

      {/* Action Buttons */}
      <div className="flex items-center space-x-2 ml-auto">
        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-50"
          title="Refresh Data"
        >
          <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
        </button>

        {/* Export Menu */}
        <Menu as="div" className="relative">
          <Menu.Button 
            className="flex items-center space-x-1 px-3 py-1 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
            disabled={isExporting}
          >
            <Download className="h-3 w-3" />
            <span>{isExporting ? 'Exporting...' : 'Export'}</span>
          </Menu.Button>
          
          <Transition
            enter="transition ease-out duration-100"
            enterFrom="transform opacity-0 scale-95"
            enterTo="transform opacity-100 scale-100"
            leave="transition ease-in duration-75"
            leaveFrom="transform opacity-100 scale-100"
            leaveTo="transform opacity-0 scale-95"
          >
            <Menu.Items className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
              <div className="py-1">
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => handleExport(['png'])}
                      className={cn(
                        'w-full text-left px-4 py-2 text-sm',
                        active && 'bg-gray-100 dark:bg-gray-700'
                      )}
                    >
                      Export as PNG
                    </button>
                  )}
                </Menu.Item>
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => handleExport(['svg'])}
                      className={cn(
                        'w-full text-left px-4 py-2 text-sm',
                        active && 'bg-gray-100 dark:bg-gray-700'
                      )}
                    >
                      Export as SVG
                    </button>
                  )}
                </Menu.Item>
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => handleExport(['csv'])}
                      className={cn(
                        'w-full text-left px-4 py-2 text-sm',
                        active && 'bg-gray-100 dark:bg-gray-700'
                      )}
                    >
                      Export Data as CSV
                    </button>
                  )}
                </Menu.Item>
                <div className="border-t border-gray-100 dark:border-gray-700">
                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={handleShare}
                        className={cn(
                          'w-full text-left px-4 py-2 text-sm',
                          active && 'bg-gray-100 dark:bg-gray-700'
                        )}
                      >
                        Share Permalink
                      </button>
                    )}
                  </Menu.Item>
                </div>
              </div>
            </Menu.Items>
          </Transition>
        </Menu>

        {/* Reset Filters */}
        {(filters.startDate || filters.endDate || filters.branchIds?.length > 0) && (
          <button
            onClick={handleResetFilters}
            className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            title="Reset Filters"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}