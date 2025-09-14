# Charts Documentation

## Overview

The BI Tool frontend includes a comprehensive data visualization system built with **Recharts**, designed for performance, accessibility, and enterprise-grade features. This documentation covers all chart components, utilities, and best practices.

## Quick Start

```jsx
import { LineChartWrapper, useChartData, ChartControls } from '../components/charts'

function DashboardChart() {
  const { data, isLoading, error } = useChartData({
    endpoint: '/api/sales-data',
    aggregation: 'day',
    startDate: '2024-01-01',
    endDate: '2024-12-31'
  })

  return (
    <div className="space-y-4">
      <ChartControls 
        filters={{ aggregation: 'day' }}
        onFiltersChange={handleFiltersChange}
        data={data}
        exportId="sales-chart"
      />
      <LineChartWrapper 
        data={data}
        xKey="date" 
        yKeys={['revenue', 'profit']}
        loading={isLoading}
        error={error}
      />
    </div>
  )
}
```

## Architecture

### Core Components

1. **Chart Wrappers** - Advanced chart components with built-in features
2. **Chart Controls** - Date range, aggregation, and export controls  
3. **Chart Legend** - Reusable legend with keyboard navigation
4. **Chart Utilities** - Performance optimization and formatting
5. **Export System** - Multi-format export (PNG, SVG, CSV)
6. **Data Hooks** - React Query integration with caching

### Design System

All charts use a centralized token system (`chart-tokens.js`) for:
- **Colors**: Colorblind-safe palettes, semantic colors, dark theme support
- **Typography**: Consistent text sizing and font weights
- **Spacing**: Standardized margins, padding, and gaps
- **Accessibility**: ARIA patterns, keyboard navigation, screen reader support

## Chart Components

### LineChartWrapper

Advanced line chart with multi-series support, brush zoom, and drill-down interactions.

**Props:**
```jsx
{
  data: Array,           // Chart data
  xKey: string,          // X-axis data key
  yKeys: Array,          // Y-axis data keys (multiple series)
  series: Array,         // Series configuration
  width: number,         // Chart width (default: auto)
  height: number,        // Chart height (default: 400)
  showBrush: boolean,    // Enable brush zoom
  showGrid: boolean,     // Show grid lines
  showLegend: boolean,   // Show legend
  onDrillDown: function, // Drill-down handler
  loading: boolean,      // Loading state
  error: object,         // Error state
  className: string      // CSS class name
}
```

**Example:**
```jsx
<LineChartWrapper 
  data={salesData}
  xKey="date" 
  yKeys={['revenue', 'profit', 'expenses']}
  showBrush={true}
  onDrillDown={(data) => console.log('Drill down:', data)}
/>
```

**Features:**
- Multi-series line support
- Brush zoom for time series
- Drill-down interactions
- Custom tooltips with formatting
- Loading and empty states
- Accessibility with hidden data table

### BarChartWrapper  

Versatile bar chart supporting horizontal/vertical orientation and stacked bars.

**Props:**
```jsx
{
  data: Array,
  xKey: string,
  yKeys: Array,
  orientation: 'vertical' | 'horizontal',
  stackId: string,       // Enable stacking
  showValues: boolean,   // Show value labels
  // ... other common props
}
```

**Example:**
```jsx
<BarChartWrapper 
  data={categoryData}
  xKey="category" 
  yKeys={['Q1', 'Q2', 'Q3', 'Q4']}
  stackId="quarters"
  orientation="horizontal"
/>
```

### PieChartWrapper

Pie chart with automatic top-N grouping and donut mode support.

**Props:**
```jsx
{
  data: Array,
  valueKey: string,      // Value field
  labelKey: string,      // Label field
  maxSlices: number,     // Top N slices (others grouped)
  innerRadius: number,   // Donut inner radius
  showPercentages: boolean,
  // ... other common props  
}
```

### AreaChartWrapper

Area chart with stacked series and individual series toggles.

**Props:**
```jsx
{
  data: Array,
  xKey: string,
  yKeys: Array,
  stackId: string,
  fillOpacity: number,
  // ... other common props
}
```

### HeatmapWrapper

Heat map for hourly/daily patterns with customizable color scales.

**Props:**
```jsx
{
  data: Array,           // Matrix data
  xKey: string,          // X-axis (e.g., hour)
  yKey: string,          // Y-axis (e.g., day)  
  valueKey: string,      // Heat value
  colorScale: Array,     // Color scale array
  showValues: boolean,   // Show cell values
  // ... other common props
}
```

### CohortRetentionChart

Specialized cohort analysis chart for customer retention visualization.

**Props:**
```jsx
{
  cohortData: Array,     // Cohort analysis data
  cohortKey: string,     // Cohort identifier
  periodKey: string,     // Time period
  retentionKey: string,  // Retention rate
  // ... other common props
}
```

## Chart Controls

### ChartControls Component

Comprehensive control panel for chart filtering and export.

**Features:**
- **Date Range**: Presets (7d, 30d, 90d) and custom picker
- **Aggregation**: Raw, hourly, daily, weekly, monthly
- **Branch Filter**: Multi-select for Super Admin users
- **Export**: PNG, SVG, CSV with progress indication
- **Share**: Permalink generation with current filters
- **Refresh**: Manual data refresh

**Example:**
```jsx
<ChartControls 
  filters={{
    startDate: '2024-01-01',
    endDate: '2024-12-31', 
    aggregation: 'day',
    branchIds: [1, 2, 3]
  }}
  onFiltersChange={(newFilters) => setFilters(newFilters)}
  branches={availableBranches}
  data={chartData}
  exportColumns={['date', 'revenue', 'profit']}
  exportId="revenue-chart"
  onRefresh={refetchData}
/>
```

### ChartLegend Component

Accessible legend with keyboard navigation and series toggles.

**Props:**
```jsx
{
  items: Array,          // Legend items
  onItemToggle: function,// Toggle handler
  layout: 'horizontal' | 'vertical',
  position: 'top' | 'bottom' | 'left' | 'right',
  showToggleAll: boolean,
  symbolType: 'square' | 'circle' | 'line',
  size: 'sm' | 'md' | 'lg',
  interactive: boolean
}
```

## Data Management

### useChartData Hook

React Query hook for optimized chart data fetching.

**Features:**
- **Caching**: Intelligent cache management with stale-while-revalidate
- **Aggregation**: Server-side aggregation preferences  
- **Downsampling**: Client-side LTTB algorithm for large datasets
- **Real-time**: WebSocket integration for live data
- **Error Handling**: Comprehensive error states and retry logic

**Example:**
```jsx
const { 
  data, 
  isLoading, 
  error, 
  refetch,
  isStale 
} = useChartData({
  endpoint: '/api/dashboard/revenue',
  filters: {
    startDate: '2024-01-01',
    endDate: '2024-12-31',
    branchIds: [1, 2, 3],
    aggregation: 'day'
  },
  options: {
    maxDataPoints: 1000,     // Trigger downsampling
    serverAggregation: true, // Prefer server aggregation
    realtime: false,         // Enable WebSocket updates
    cacheTime: 5 * 60 * 1000 // 5 minute cache
  }
})
```

### Specialized Data Hooks

```jsx
// KPI metrics
const { metrics } = useKpiData({ dateRange, branches })

// Dashboard summary  
const { summary } = useDashboardData({ role: 'branch_manager' })

// Sales analysis
const { sales } = useSalesData({ 
  groupBy: 'product',
  timeframe: 'month' 
})
```

## Performance Optimization

### Large Dataset Handling

The chart system automatically handles large datasets with:

1. **LTTB Downsampling**: Largest-Triangle-Three-Buckets algorithm
   ```jsx
   import { downsampleLTTB } from '../charts/chartUtils'
   
   const optimizedData = downsampleLTTB(largeDataset, 1000) // 1000 points
   ```

2. **Server-side Aggregation**: Automatic aggregation hints
   ```jsx
   useChartData({
     endpoint: '/api/sales',
     options: { 
       maxDataPoints: 500,
       serverAggregation: true // Request pre-aggregated data
     }
   })
   ```

3. **Virtualization**: For large legends and data tables
   ```jsx
   import { FixedSizeList as List } from 'react-window'
   ```

### Optimization Guidelines

- **Data Points**: Keep under 1000 points per series for smooth rendering
- **Series Limit**: Maximum 10 series for readability  
- **Updates**: Use `useMemo` for expensive calculations
- **Re-renders**: Memoize chart components when data doesn't change

## Accessibility Features

### Screen Reader Support

All charts include:
- **Hidden Data Tables**: Complete data in table format
- **ARIA Labels**: Descriptive chart and data point labels  
- **Live Regions**: Dynamic content announcements
- **Keyboard Navigation**: Full keyboard accessibility

### Visual Accessibility

- **Color Blind Support**: Colorblind-safe palettes and patterns
- **High Contrast**: Dark theme with proper contrast ratios
- **Text Alternatives**: All visual information available as text
- **Focus Management**: Clear focus indicators and logical tab order

### Implementation Example

```jsx
<LineChartWrapper 
  data={data}
  xKey="date"
  yKeys={['revenue']}
  aria-label="Revenue trend over time"
  aria-describedby="chart-description"
/>
<div id="chart-description" className="sr-only">
  Line chart showing revenue from {startDate} to {endDate} 
  with {dataPoints} data points
</div>
```

## Export System

### Multi-format Export

```jsx
import { exportMultipleFormats } from '../charts/exportUtils'

// Export chart as PNG and data as CSV
const results = await exportMultipleFormats(
  'chart-id',           // DOM element ID
  chartData,            // Data array  
  ['date', 'revenue'],  // CSV columns
  'revenue-analysis',   // Base filename
  ['png', 'csv']        // Export formats
)
```

### Export Options

- **PNG**: High-resolution image (2x pixel density)
- **SVG**: Vector format with embedded styles  
- **CSV**: Raw data with custom column selection
- **PDF**: Server-side rendering for complex reports
- **Permalink**: Shareable URLs with current filter state

### Server-side Export

For large datasets or complex layouts:

```jsx
const { jobId } = await requestServerExport({
  chartConfig,
  data,
  format: 'pdf',
  layout: 'a4-landscape'
})

// Poll for completion
const result = await pollExportJob(jobId)
```

## Testing

### Component Testing

```jsx
import { render, screen } from '@testing-library/react'
import { LineChartWrapper } from '../charts'

test('renders line chart with data', () => {
  const data = [
    { date: '2024-01-01', revenue: 1000 },
    { date: '2024-01-02', revenue: 1200 }
  ]
  
  render(
    <LineChartWrapper 
      data={data}
      xKey="date" 
      yKeys={['revenue']}
    />
  )
  
  expect(screen.getByRole('img', { name: /line chart/i })).toBeInTheDocument()
})
```

### Utility Testing

```jsx
import { formatCurrency, downsampleLTTB } from '../charts/chartUtils'

test('formats currency correctly', () => {
  expect(formatCurrency(1234.56)).toBe('$1,234.56')
})

test('downsamples data maintaining trends', () => {
  const data = generateLargeDataset(10000) // 10k points
  const downsampled = downsampleLTTB(data, 100) // 100 points
  
  expect(downsampled).toHaveLength(100)
  expect(preservesTrends(data, downsampled)).toBe(true)
})
```

## Best Practices

### Data Structure

Use consistent data structures:
```jsx
// Time series data
const timeSeriesData = [
  { date: '2024-01-01', revenue: 1000, profit: 200 },
  { date: '2024-01-02', revenue: 1200, profit: 250 }
]

// Categorical data  
const categoryData = [
  { category: 'Electronics', sales: 5000 },
  { category: 'Clothing', sales: 3000 }
]
```

### Performance

```jsx
// ✅ Good: Memoize expensive calculations
const processedData = useMemo(() => {
  return data.map(item => ({
    ...item,
    calculated: expensiveCalculation(item)
  }))
}, [data])

// ❌ Bad: Recalculate on every render
const processedData = data.map(item => ({
  ...item, 
  calculated: expensiveCalculation(item)
}))
```

### Accessibility

```jsx
// ✅ Good: Descriptive labels
<LineChartWrapper 
  data={data}
  aria-label="Monthly revenue trend showing 15% growth"
/>

// ❌ Bad: Generic labels  
<LineChartWrapper 
  data={data}
  aria-label="Chart"
/>
```

### Error Handling

```jsx
// ✅ Good: Comprehensive error handling
const { data, error, isLoading } = useChartData(endpoint)

if (error) {
  return <ChartError error={error} onRetry={refetch} />
}

// ❌ Bad: Silent failures
const { data } = useChartData(endpoint)
return <LineChart data={data || []} />
```

## Migration Guide

### From Legacy Components

Replace old chart components:
```jsx
// ❌ Old
import { LineChartComponent } from '../components/charts'
<LineChartComponent data={data} />

// ✅ New  
import { LineChartWrapper } from '../components/charts'
<LineChartWrapper data={data} xKey="date" yKeys={['value']} />
```

### Breaking Changes

- **Props**: Chart wrappers use `xKey`/`yKeys` instead of automatic detection
- **Styling**: Custom styles should use chart tokens instead of hardcoded values
- **Data**: Expects array of objects with consistent keys
- **Events**: New event handler signatures with additional context

## Troubleshooting

### Common Issues

**Chart not rendering:**
- Check data format (array of objects)
- Verify `xKey` and `yKeys` exist in data
- Ensure container has defined dimensions

**Performance issues:**
- Enable downsampling for datasets > 1000 points
- Use server-side aggregation when possible  
- Memoize data processing functions

**Export failures:**
- Verify DOM element exists before export
- Check browser canvas size limits
- Ensure chart is fully rendered

### Debug Mode

Enable debug logging:
```jsx
import { setChartDebug } from '../charts/chartUtils'

// Enable debug mode
setChartDebug(true)

// Charts will log performance metrics and warnings
```

## API Reference

For complete API documentation, see individual component files or use TypeScript definitions for IntelliSense support.

---

## Support

For questions or issues:
1. Check this documentation
2. Review component examples in `/src/pages/dashboard/`
3. Check browser console for warnings
4. Review network requests for data loading issues