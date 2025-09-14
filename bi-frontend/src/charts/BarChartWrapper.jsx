/**
 * BarChartWrapper Component
 * Advanced bar chart with grouped/stacked bars, horizontal/vertical modes, and accessibility
 */

import React, { useMemo, useCallback, useState, useRef } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell
} from 'recharts'
import { chartTokens } from '../styles/chart-tokens'
import { formatNumber, formatDate } from './chartUtils'
import { cn } from '../utils'

/**
 * BarChartWrapper Component
 * @param {Object} props - Component props
 * @param {Array} props.data - Chart data array
 * @param {string} props.xKey - Property name for x-axis
 * @param {Array|string} props.yKeys - Property name(s) for y-axis
 * @param {Array} props.series - Series configuration array
 * @param {number} props.height - Chart height
 * @param {number|string} props.width - Chart width
 * @param {boolean} props.loading - Loading state
 * @param {Function} props.onPointClick - Bar click handler
 * @param {Function} props.tooltipFormatter - Tooltip formatter
 * @param {Function} props.yAxisFormatter - Y-axis formatter
 * @param {string} props.exportId - Element ID for export
 * @param {boolean} props.showGrid - Show grid lines
 * @param {boolean} props.showLegend - Show legend
 * @param {boolean} props.stacked - Stack bars
 * @param {boolean} props.horizontal - Horizontal bar chart
 * @param {string} props.layout - Chart layout (vertical or horizontal)
 * @param {number} props.topN - Show only top N items
 * @param {string} props.className - CSS class name
 * @param {Object} props.margin - Chart margins
 */
export default function BarChartWrapper({
  data = [],
  xKey = 'name',
  yKeys = ['value'],
  series = [],
  height = 300,
  width = '100%',
  loading = false,
  onPointClick = () => {},
  tooltipFormatter = (value, name) => [formatNumber(value), name],
  yAxisFormatter = (value) => formatNumber(value, { compact: true }),
  exportId = 'bar-chart',
  showGrid = true,
  showLegend = true,
  stacked = false,
  horizontal = false,
  layout = 'vertical',
  topN = null,
  className = '',
  margin = chartTokens.dimensions.margin.normal,
  ...props
}) {
  const chartRef = useRef(null)
  const [hiddenSeries, setHiddenSeries] = useState(new Set())
  const [hoveredBar, setHoveredBar] = useState(null)

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
      color: chartTokens.colors.primary[index % chartTokens.colors.primary.length]
    }))
  }, [series, yKeys])

  // Process data - handle topN filtering and sorting
  const processedData = useMemo(() => {
    let result = [...data]
    
    // If topN is specified, sort and limit data
    if (topN && topN > 0) {
      const primarySeries = processedSeries[0]
      if (primarySeries) {
        result = result
          .sort((a, b) => (b[primarySeries.key] || 0) - (a[primarySeries.key] || 0))
          .slice(0, topN)
      }
    }
    
    return result
  }, [data, topN, processedSeries])

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
          {label}
        </div>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center space-x-2 text-sm">
            <div 
              className="w-3 h-3 rounded" 
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-600 dark:text-gray-300">{entry.name}:</span>
            <span className="font-semibold text-gray-900 dark:text-white">
              {tooltipFormatter(entry.value, entry.name)[0]}
            </span>
          </div>
        ))}
        <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-500 dark:text-gray-400">
          Click bar to drill down
        </div>
      </div>
    )
  }, [tooltipFormatter])

  // Handle bar click for drill-down
  const handleBarClick = useCallback((data, index, event) => {
    event.stopPropagation()
    onPointClick({
      xValue: data[xKey],
      row: data,
      index
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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 00-2-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">No data available</p>
        </div>
      </div>
    )
  }

  const isHorizontal = horizontal || layout === 'horizontal'

  return (
    <div 
      id={exportId}
      className={cn('w-full', className)}
      style={{ height, width }}
      role="region"
      aria-label={`${isHorizontal ? 'Horizontal' : 'Vertical'} bar chart visualization`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          ref={chartRef}
          data={processedData}
          margin={margin}
          layout={isHorizontal ? 'horizontal' : 'vertical'}
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
          
          {/* Axes */}
          {isHorizontal ? (
            <>
              <XAxis 
                type="number"
                tickFormatter={yAxisFormatter}
                stroke={chartTokens.colors.neutral[400]}
                fontSize={chartTokens.typography.fontSize.sm}
                tick={{ fill: chartTokens.colors.neutral[600] }}
              />
              <YAxis 
                type="category"
                dataKey={xKey}
                stroke={chartTokens.colors.neutral[400]}
                fontSize={chartTokens.typography.fontSize.sm}
                tick={{ fill: chartTokens.colors.neutral[600] }}
                width={100}
              />
            </>
          ) : (
            <>
              <XAxis 
                dataKey={xKey}
                stroke={chartTokens.colors.neutral[400]}
                fontSize={chartTokens.typography.fontSize.sm}
                tick={{ fill: chartTokens.colors.neutral[600] }}
                angle={processedData.length > 5 ? -45 : 0}
                textAnchor={processedData.length > 5 ? 'end' : 'middle'}
                height={processedData.length > 5 ? 60 : 30}
              />
              <YAxis 
                tickFormatter={yAxisFormatter}
                stroke={chartTokens.colors.neutral[400]}
                fontSize={chartTokens.typography.fontSize.sm}
                tick={{ fill: chartTokens.colors.neutral[600] }}
              />
            </>
          )}
          
          {/* Tooltip */}
          <Tooltip content={<CustomTooltip />} />
          
          {/* Legend */}
          {showLegend && processedSeries.length > 1 && (
            <Legend 
              onClick={handleLegendClick}
              wrapperStyle={{ cursor: 'pointer', paddingTop: '20px' }}
              iconType="rect"
            />
          )}
          
          {/* Bars */}
          {processedSeries.map((s, seriesIndex) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.label}
              fill={s.color || chartTokens.colors.primary[seriesIndex]}
              stackId={stacked ? 'stack' : undefined}
              onClick={handleBarClick}
              onMouseEnter={(data, index) => setHoveredBar(`${seriesIndex}-${index}`)}
              onMouseLeave={() => setHoveredBar(null)}
              style={{ cursor: 'pointer' }}
              isAnimationActive={true}
              animationDuration={chartTokens.animation.duration.normal}
              opacity={hiddenSeries.has(s.key) ? 0 : 1}
            >
              {/* Custom colors for single series bars */}
              {processedSeries.length === 1 && processedData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={
                    hoveredBar === `${seriesIndex}-${index}` 
                      ? chartTokens.colors.primary[(index + 1) % chartTokens.colors.primary.length]
                      : s.color || chartTokens.colors.primary[index % chartTokens.colors.primary.length]
                  }
                />
              ))}
            </Bar>
          ))}
        </BarChart>
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
          {processedData.slice(0, 10).map((item, index) => (
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