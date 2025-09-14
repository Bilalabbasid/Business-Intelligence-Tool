/**
 * PieChartWrapper Component
 * Advanced pie chart with top N grouping, accessibility, and slice interactions
 */

import React, { useMemo, useCallback, useState } from 'react'
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  LabelList
} from 'recharts'
import { chartTokens } from '../styles/chart-tokens'
import { formatNumber } from './chartUtils'
import { cn } from '../utils'

/**
 * PieChartWrapper Component
 * @param {Object} props - Component props
 * @param {Array} props.data - Chart data array
 * @param {string} props.dataKey - Property name for values
 * @param {string} props.nameKey - Property name for labels
 * @param {number} props.height - Chart height
 * @param {number|string} props.width - Chart width
 * @param {boolean} props.loading - Loading state
 * @param {Function} props.onSliceClick - Slice click handler
 * @param {Function} props.tooltipFormatter - Tooltip formatter
 * @param {string} props.exportId - Element ID for export
 * @param {boolean} props.showLegend - Show legend
 * @param {boolean} props.showLabels - Show slice labels
 * @param {boolean} props.showPercentages - Show percentages on slices
 * @param {number} props.topN - Show only top N slices (rest grouped as "Other")
 * @param {number} props.innerRadius - Inner radius for donut chart
 * @param {number} props.outerRadius - Outer radius
 * @param {Array} props.colors - Custom color palette
 * @param {string} props.className - CSS class name
 * @param {boolean} props.explodeOnHover - Explode slice on hover
 */
export default function PieChartWrapper({
  data = [],
  dataKey = 'value',
  nameKey = 'name',
  height = 300,
  width = '100%',
  loading = false,
  onSliceClick = () => {},
  tooltipFormatter = (value, name) => [formatNumber(value), name],
  exportId = 'pie-chart',
  showLegend = true,
  showLabels = true,
  showPercentages = true,
  topN = 5,
  innerRadius = 0,
  outerRadius = '80%',
  colors = chartTokens.colors.primary,
  className = '',
  explodeOnHover = true,
  ...props
}) {
  const [activeIndex, setActiveIndex] = useState(-1)
  const [explodedSlices, setExplodedSlices] = useState(new Set())

  // Process data - handle topN grouping
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return []
    
    // Sort by value descending
    const sorted = [...data].sort((a, b) => (b[dataKey] || 0) - (a[dataKey] || 0))
    
    if (!topN || sorted.length <= topN) {
      return sorted
    }
    
    // Take top N items
    const topItems = sorted.slice(0, topN)
    const otherItems = sorted.slice(topN)
    
    // Sum remaining items as "Other"
    const otherValue = otherItems.reduce((sum, item) => sum + (item[dataKey] || 0), 0)
    
    if (otherValue > 0) {
      return [
        ...topItems,
        {
          [nameKey]: 'Other',
          [dataKey]: otherValue,
          isOther: true,
          count: otherItems.length
        }
      ]
    }
    
    return topItems
  }, [data, dataKey, nameKey, topN])

  // Calculate total for percentage calculations
  const total = useMemo(() => {
    return processedData.reduce((sum, item) => sum + (item[dataKey] || 0), 0)
  }, [processedData, dataKey])

  // Custom label renderer
  const renderLabel = useCallback((entry) => {
    if (!showLabels) return null
    
    const percentage = ((entry[dataKey] / total) * 100).toFixed(1)
    
    if (showPercentages) {
      return `${percentage}%`
    }
    
    return entry[nameKey]
  }, [showLabels, showPercentages, dataKey, total, nameKey])

  // Custom tooltip component
  const CustomTooltip = useCallback(({ active, payload }) => {
    if (!active || !payload || payload.length === 0) return null
    
    const data = payload[0].payload
    const percentage = ((data[dataKey] / total) * 100).toFixed(1)
    
    return (
      <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg">
        <div className="text-sm font-medium text-gray-900 dark:text-white mb-1">
          {data[nameKey]}
        </div>
        <div className="flex items-center space-x-2 text-sm">
          <div 
            className="w-3 h-3 rounded-full" 
            style={{ backgroundColor: payload[0].color }}
          />
          <span className="text-gray-600 dark:text-gray-300">Value:</span>
          <span className="font-semibold text-gray-900 dark:text-white">
            {tooltipFormatter(data[dataKey], data[nameKey])[0]}
          </span>
        </div>
        <div className="text-sm text-gray-600 dark:text-gray-300 mt-1">
          {percentage}% of total
          {data.isOther && (
            <span className="block text-xs text-gray-500 dark:text-gray-400">
              ({data.count} items grouped)
            </span>
          )}
        </div>
        <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-500 dark:text-gray-400">
          Click slice to drill down
        </div>
      </div>
    )
  }, [tooltipFormatter, dataKey, total, nameKey])

  // Handle slice click
  const handleSliceClick = useCallback((data, index) => {
    onSliceClick({
      name: data[nameKey],
      value: data[dataKey],
      percentage: ((data[dataKey] / total) * 100),
      row: data,
      index
    })
  }, [onSliceClick, nameKey, dataKey, total])

  // Handle mouse enter for hover effects
  const handleMouseEnter = useCallback((data, index) => {
    setActiveIndex(index)
    if (explodeOnHover) {
      setExplodedSlices(prev => new Set([...prev, index]))
    }
  }, [explodeOnHover])

  // Handle mouse leave
  const handleMouseLeave = useCallback(() => {
    setActiveIndex(-1)
    if (explodeOnHover) {
      setExplodedSlices(new Set())
    }
  }, [explodeOnHover])

  // Custom legend renderer
  const renderLegend = useCallback((props) => {
    const { payload } = props
    
    return (
      <ul className="flex flex-wrap justify-center gap-4 mt-4">
        {payload.map((entry, index) => {
          const data = processedData[index]
          const percentage = ((data[dataKey] / total) * 100).toFixed(1)
          
          return (
            <li 
              key={index}
              className="flex items-center space-x-2 text-sm cursor-pointer hover:opacity-75"
              onClick={() => handleSliceClick(data, index)}
            >
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-gray-700 dark:text-gray-300">
                {entry.value} ({percentage}%)
              </span>
            </li>
          )
        })}
      </ul>
    )
  }, [processedData, dataKey, total, handleSliceClick])

  // Loading state
  if (loading) {
    return (
      <div 
        className={cn('flex items-center justify-center', className)}
        style={{ height, width }}
        role="status" 
        aria-label="Loading chart data"
      >
        <div className="flex flex-col items-center space-y-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading chart...</p>
        </div>
      </div>
    )
  }

  // Empty state
  if (!processedData || processedData.length === 0) {
    return (
      <div 
        className={cn('flex items-center justify-center', className)}
        style={{ height, width }}
        role="img"
        aria-label="No chart data available"
      >
        <div className="text-center">
          <div className="text-gray-400 dark:text-gray-500 mb-2">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">No data available</p>
        </div>
      </div>
    )
  }

  return (
    <div 
      id={exportId}
      className={cn('w-full', className)}
      style={{ height, width }}
      role="region"
      aria-label="Pie chart visualization"
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart {...props}>
          <Pie
            data={processedData}
            cx="50%"
            cy="50%"
            outerRadius={outerRadius}
            innerRadius={innerRadius}
            dataKey={dataKey}
            onClick={handleSliceClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            isAnimationActive={true}
            animationDuration={chartTokens.animation.duration.normal}
          >
            {processedData.map((entry, index) => (
              <Cell 
                key={`cell-${index}`}
                fill={colors[index % colors.length]}
                stroke={activeIndex === index ? '#ffffff' : 'none'}
                strokeWidth={activeIndex === index ? 2 : 0}
                style={{ 
                  cursor: 'pointer',
                  filter: activeIndex === index ? 'brightness(1.1)' : 'none'
                }}
                onMouseEnter={() => handleMouseEnter(entry, index)}
                onMouseLeave={handleMouseLeave}
              />
            ))}
            {showLabels && (
              <LabelList
                dataKey={renderLabel}
                position="center"
                fill="#ffffff"
                fontSize={12}
                fontWeight="bold"
              />
            )}
          </Pie>
          
          <Tooltip content={<CustomTooltip />} />
          
          {showLegend && (
            <Legend content={renderLegend} />
          )}
        </PieChart>
      </ResponsiveContainer>
      
      {/* Accessibility: Hidden data table */}
      <table className="sr-only" aria-label="Chart data table">
        <thead>
          <tr>
            <th>Category</th>
            <th>Value</th>
            <th>Percentage</th>
          </tr>
        </thead>
        <tbody>
          {processedData.map((item, index) => {
            const percentage = ((item[dataKey] / total) * 100).toFixed(1)
            return (
              <tr key={index}>
                <td>{item[nameKey]}</td>
                <td>{item[dataKey]}</td>
                <td>{percentage}%</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}