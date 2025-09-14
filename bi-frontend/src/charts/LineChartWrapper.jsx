/**
 * LineChartWrapper Component
 * Advanced line chart with multi-series support, interactions, and accessibility
 */

import React, { useMemo, useCallback, useState, useRef } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Brush,
  ReferenceLine
} from 'recharts'
import { chartTokens } from '../styles/chart-tokens'
import { formatNumber, formatDate } from './chartUtils'
import { cn } from '../utils'

/**
 * LineChartWrapper Component
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
 * @param {string} props.aggregation - Data aggregation level
 * @param {string} props.exportId - Element ID for export
 * @param {boolean} props.showGrid - Show grid lines
 * @param {boolean} props.showLegend - Show legend
 * @param {boolean} props.showBrush - Show brush for zooming
 * @param {boolean} props.showDots - Show data points
 * @param {boolean} props.stacked - Stack lines
 * @param {Array} props.referenceLines - Reference lines config
 * @param {string} props.className - CSS class name
 * @param {Object} props.margin - Chart margins
 */
export default function LineChartWrapper({
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
  aggregation = 'raw',
  exportId = 'line-chart',
  showGrid = true,
  showLegend = true,
  showBrush = false,
  showDots = true,
  stacked = false,
  referenceLines = [],
  className = '',
  margin = chartTokens.dimensions.margin.normal,
  ...props
}) {
  const chartRef = useRef(null)
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
      strokeWidth: 2
    }))
  }, [series, yKeys])

  // Filter data for visible series
  const visibleData = useMemo(() => {
    if (hiddenSeries.size === 0) return data
    
    return data.map(item => {
      const filteredItem = { ...item }
      processedSeries.forEach(s => {
        if (hiddenSeries.has(s.key)) {
          delete filteredItem[s.key]
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

    return (
      <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg">
        <div className="text-sm font-medium text-gray-900 dark:text-white mb-2">
          {formatDate(label)}
        </div>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center space-x-2 text-sm">
            <div 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-600 dark:text-gray-300">{entry.name}:</span>
            <span className="font-semibold text-gray-900 dark:text-white">
              {tooltipFormatter(entry.value, entry.name)[0]}
            </span>
          </div>
        ))}
        {payload.length > 1 && (
          <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-500 dark:text-gray-400">
            Click point to drill down
          </div>
        )}
      </div>
    )
  }, [tooltipFormatter])

  // Handle point click for drill-down
  const handleActiveDotClick = useCallback((data, payload, event) => {
    event.stopPropagation()
    onPointClick({
      xValue: payload.payload[xKey],
      seriesKey: payload.dataKey,
      row: payload.payload,
      aggregation
    })
  }, [onPointClick, xKey, aggregation])

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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 00-2-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
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
      aria-label="Line chart visualization"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          ref={chartRef}
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
          <Tooltip 
            content={<CustomTooltip />}
            cursor={{ stroke: chartTokens.colors.primary[0], strokeWidth: 1 }}
          />
          
          {/* Legend */}
          {showLegend && (
            <Legend 
              onClick={handleLegendClick}
              wrapperStyle={{ cursor: 'pointer', paddingTop: '20px' }}
              iconType="line"
            />
          )}
          
          {/* Reference lines */}
          {referenceLines.map((line, index) => (
            <ReferenceLine
              key={index}
              y={line.value}
              stroke={line.color || chartTokens.colors.neutral[400]}
              strokeDasharray={line.strokeDasharray || "5 5"}
              label={line.label}
            />
          ))}
          
          {/* Lines */}
          {processedSeries.map((s, index) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={hiddenSeries.has(s.key) ? 'transparent' : (s.color || chartTokens.colors.primary[index])}
              strokeWidth={s.strokeWidth || 2}
              dot={showDots && !hiddenSeries.has(s.key) ? { 
                r: 3, 
                fill: s.color || chartTokens.colors.primary[index],
                onMouseEnter: () => setHoveredSeries(s.key),
                onMouseLeave: () => setHoveredSeries(null)
              } : false}
              activeDot={{ 
                r: 6, 
                onClick: handleActiveDotClick,
                style: { cursor: 'pointer' },
                onMouseEnter: () => setHoveredSeries(s.key),
                onMouseLeave: () => setHoveredSeries(null)
              }}
              connectNulls={false}
              isAnimationActive={true}
              animationDuration={chartTokens.animation.duration.normal}
              opacity={hoveredSeries && hoveredSeries !== s.key ? 0.3 : 1}
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
        </LineChart>
      </ResponsiveContainer>
      
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