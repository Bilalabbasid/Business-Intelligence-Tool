/**
 * AreaChartWrapper Component
 * Advanced area chart with stacked areas, series toggles, and accessibility
 */

import React, { useMemo, useCallback, useState } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Brush
} from 'recharts'
import { chartTokens } from '../styles/chart-tokens'
import { formatNumber, formatDate } from './chartUtils'
import { cn } from '../utils'

/**
 * AreaChartWrapper Component
 * @param {Object} props - Component props
 * @param {Array} props.data - Chart data array
 * @param {string} props.xKey - Property name for x-axis
 * @param {Array|string} props.yKeys - Property name(s) for y-axis
 * @param {Array} props.series - Series configuration array
 * @param {number} props.height - Chart height
 * @param {number|string} props.width - Chart width
 * @param {boolean} props.loading - Loading state
 * @param {Function} props.onPointClick - Point click handler
 * @param {Function} props.tooltipFormatter - Tooltip formatter
 * @param {Function} props.yAxisFormatter - Y-axis formatter
 * @param {string} props.exportId - Element ID for export
 * @param {boolean} props.showGrid - Show grid lines
 * @param {boolean} props.showLegend - Show legend
 * @param {boolean} props.showBrush - Show brush for zooming
 * @param {boolean} props.stacked - Stack areas
 * @param {string} props.stackId - Stack ID for grouping
 * @param {string} props.className - CSS class name
 * @param {Object} props.margin - Chart margins
 */
export default function AreaChartWrapper({
  data = [],
  xKey = 'date',
  yKeys = ['value'],
  series = [],
  height = 300,
  width = '100%',
  loading = false,
  onPointClick = () => {},
  tooltipFormatter = (value, name) => [formatNumber(value), name],
  yAxisFormatter = (value) => formatNumber(value, { compact: true }),
  exportId = 'area-chart',
  showGrid = true,
  showLegend = true,
  showBrush = false,
  stacked = true,
  stackId = 'default',
  className = '',
  margin = chartTokens.dimensions.margin.normal,
  ...props
}) {
  const [hiddenSeries, setHiddenSeries] = useState(new Set())
  const [hoveredSeries, setHoveredSeries] = useState(null)

  // Process series configuration
  const processedSeries = useMemo(() => {
    if (series.length > 0) {
      return series
    }
    
    // Auto-generate series from yKeys
    const keys = Array.isArray(yKeys) ? yKeys : [yKeys]
    return keys.map((key, index) => ({
      key,
      label: key.charAt(0).toUpperCase() + key.slice(1),
      color: chartTokens.colors.primary[index % chartTokens.colors.primary.length],
      fillOpacity: 0.6
    }))
  }, [series, yKeys])

  // Filter data for visible series
  const visibleData = useMemo(() => {
    if (hiddenSeries.size === 0) return data
    
    return data.map(item => {
      const filteredItem = { ...item }
      processedSeries.forEach(s => {
        if (hiddenSeries.has(s.key)) {
          filteredItem[s.key] = 0 // Set to 0 instead of deleting for stacked areas
        }
      })
      return filteredItem
    })
  }, [data, processedSeries, hiddenSeries])

  // Handle legend click to toggle series visibility
  const handleLegendClick = useCallback((entry) => {
    setHiddenSeries(prev => {
      const newSet = new Set(prev)
      if (newSet.has(entry.value)) {
        newSet.delete(entry.value)
      } else {
        newSet.add(entry.value)
      }
      return newSet
    })
  }, [])

  // Custom tooltip component
  const CustomTooltip = useCallback(({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null

    // Calculate total for percentage display
    const total = payload.reduce((sum, entry) => sum + (entry.value || 0), 0)

    return (
      <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg">
        <div className="text-sm font-medium text-gray-900 dark:text-white mb-2">
          {formatDate(label)}
        </div>
        {total > 0 && (
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            Total: {formatNumber(total)}
          </div>
        )}
        {payload
          .filter(entry => entry.value > 0)
          .sort((a, b) => b.value - a.value)
          .map((entry, index) => {
            const percentage = total > 0 ? ((entry.value / total) * 100).toFixed(1) : 0
            return (
              <div key={index} className="flex items-center justify-between space-x-4 text-sm">
                <div className="flex items-center space-x-2">
                  <div 
                    className="w-3 h-3 rounded" 
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="text-gray-600 dark:text-gray-300">{entry.name}:</span>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-gray-900 dark:text-white">
                    {tooltipFormatter(entry.value, entry.name)[0]}
                  </div>
                  {stacked && (
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {percentage}%
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-500 dark:text-gray-400">
          Click area to drill down
        </div>
      </div>
    )
  }, [tooltipFormatter, stacked])

  // Handle area click for drill-down
  const handleActiveDotClick = useCallback((data, payload, event) => {
    event.stopPropagation()
    onPointClick({
      xValue: payload.payload[xKey],
      seriesKey: payload.dataKey,
      row: payload.payload
    })
  }, [onPointClick, xKey])

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
  if (!data || data.length === 0) {
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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
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
      aria-label="Area chart visualization"
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={visibleData}
          margin={margin}
          {...props}
        >
          {/* Grid */}
          {showGrid && (
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke={chartTokens.colors.neutral[200]}
              strokeOpacity={0.5}
            />
          )}
          
          {/* X-axis */}
          <XAxis 
            dataKey={xKey}
            tickFormatter={formatDate}
            stroke={chartTokens.colors.neutral[400]}
            fontSize={chartTokens.typography.fontSize.sm}
            tick={{ fill: chartTokens.colors.neutral[600] }}
          />
          
          {/* Y-axis */}
          <YAxis 
            tickFormatter={yAxisFormatter}
            stroke={chartTokens.colors.neutral[400]}
            fontSize={chartTokens.typography.fontSize.sm}
            tick={{ fill: chartTokens.colors.neutral[600] }}
          />
          
          {/* Tooltip */}
          <Tooltip content={<CustomTooltip />} />
          
          {/* Legend */}
          {showLegend && (
            <Legend 
              onClick={handleLegendClick}
              wrapperStyle={{ cursor: 'pointer', paddingTop: '20px' }}
              iconType="rect"
            />
          )}
          
          {/* Areas - render in reverse order for proper stacking */}
          {processedSeries.slice().reverse().map((s, index) => (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stackId={stacked ? stackId : s.key}
              stroke={s.color || chartTokens.colors.primary[index]}
              fill={s.color || chartTokens.colors.primary[index]}
              fillOpacity={hiddenSeries.has(s.key) ? 0 : (s.fillOpacity || 0.6)}
              strokeWidth={2}
              dot={false}
              activeDot={{ 
                r: 4, 
                onClick: handleActiveDotClick,
                style: { cursor: 'pointer' }
              }}
              connectNulls={false}
              isAnimationActive={true}
              animationDuration={chartTokens.animation.duration.normal}
              onMouseEnter={() => setHoveredSeries(s.key)}
              onMouseLeave={() => setHoveredSeries(null)}
              opacity={hoveredSeries && hoveredSeries !== s.key ? 0.5 : 1}
            />
          ))}
          
          {/* Brush for zooming */}
          {showBrush && (
            <Brush 
              dataKey={xKey}
              height={30}
              stroke={chartTokens.colors.primary[0]}
              fill={chartTokens.colors.primary[0] + '20'}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
      
      {/* Series toggle controls */}
      {processedSeries.length > 1 && (
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {processedSeries.map((s, index) => (
            <button
              key={s.key}
              onClick={() => handleLegendClick({ value: s.key })}
              className={cn(
                'px-3 py-1 text-xs rounded-full border transition-colors',
                hiddenSeries.has(s.key)
                  ? 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600'
                  : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 shadow-sm'
              )}
              style={{
                borderColor: hiddenSeries.has(s.key) ? undefined : s.color,
                backgroundColor: hiddenSeries.has(s.key) ? undefined : s.color + '20'
              }}
            >
              <div className="flex items-center space-x-1">
                <div 
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: s.color }}
                />
                <span>{s.label}</span>
              </div>
            </button>
          ))}
        </div>
      )}
      
      {/* Accessibility: Hidden data table */}
      <table className="sr-only" aria-label="Chart data table">
        <thead>
          <tr>
            <th>{xKey}</th>
            {processedSeries.map(s => (
              <th key={s.key}>{s.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 10).map((item, index) => (
            <tr key={index}>
              <td>{item[xKey]}</td>
              {processedSeries.map(s => (
                <td key={s.key}>{item[s.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}