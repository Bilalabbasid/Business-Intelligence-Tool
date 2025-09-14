/**
 * Chart Examples - Complete Usage Guide
 * Demonstrates all chart components with real-world scenarios
 */

import React, { useState, useMemo } from 'react'
import {
  LineChartWrapper,
  BarChartWrapper, 
  PieChartWrapper,
  AreaChartWrapper,
  HeatmapWrapper,
  CohortRetentionChart,
  ChartControls,
  ChartLegend,
  useChartData,
  generateLegendItems
} from '../components/charts'

// Sample data for demonstrations
const sampleRevenueData = [
  { date: '2024-01-01', revenue: 12000, profit: 3000, expenses: 9000 },
  { date: '2024-01-02', revenue: 15000, profit: 4500, expenses: 10500 },
  { date: '2024-01-03', revenue: 11000, profit: 2200, expenses: 8800 },
  { date: '2024-01-04', revenue: 18000, profit: 5400, expenses: 12600 },
  { date: '2024-01-05', revenue: 16000, profit: 4800, expenses: 11200 }
]

const sampleCategoryData = [
  { category: 'Electronics', Q1: 25000, Q2: 28000, Q3: 31000, Q4: 35000 },
  { category: 'Clothing', Q1: 18000, Q2: 22000, Q3: 19000, Q4: 24000 },
  { category: 'Books', Q1: 8000, Q2: 9500, Q3: 11000, Q4: 12500 },
  { category: 'Home & Garden', Q1: 15000, Q2: 18000, Q3: 21000, Q4: 19000 }
]

const sampleProductData = [
  { name: 'Laptops', value: 45, revenue: 450000 },
  { name: 'Smartphones', value: 30, revenue: 300000 },
  { name: 'Tablets', value: 15, revenue: 150000 },
  { name: 'Accessories', value: 10, revenue: 100000 }
]

const sampleHeatmapData = [
  { hour: 9, day: 'Monday', sales: 25 },
  { hour: 10, day: 'Monday', sales: 45 },
  { hour: 11, day: 'Monday', sales: 65 },
  { hour: 9, day: 'Tuesday', sales: 30 },
  { hour: 10, day: 'Tuesday', sales: 50 },
  { hour: 11, day: 'Tuesday', sales: 70 }
]

export default function ChartExamples() {
  const [filters, setFilters] = useState({
    startDate: '2024-01-01',
    endDate: '2024-12-31',
    aggregation: 'day',
    branchIds: []
  })

  const [legendItems, setLegendItems] = useState([
    { id: 'revenue', label: 'Revenue', color: '#3B82F6', visible: true },
    { id: 'profit', label: 'Profit', color: '#10B981', visible: true },
    { id: 'expenses', label: 'Expenses', color: '#EF4444', visible: false }
  ])

  // Real data fetching example
  const { data: revenueData, isLoading, error } = useChartData({
    endpoint: '/api/dashboard/revenue',
    filters,
    options: {
      maxDataPoints: 1000,
      serverAggregation: true
    }
  })

  // Handle legend toggle
  const handleLegendToggle = (itemId, visible) => {
    setLegendItems(items => 
      items.map(item => 
        item.id === itemId ? { ...item, visible } : item
      )
    )
  }

  // Visible series based on legend
  const visibleSeries = useMemo(() => 
    legendItems.filter(item => item.visible).map(item => item.id),
    [legendItems]
  )

  return (
    <div className="space-y-8 p-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
        Chart Examples & Integration Guide
      </h1>

      {/* Chart Controls Example */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Chart Controls</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800">
          <ChartControls
            filters={filters}
            onFiltersChange={setFilters}
            branches={[
              { id: 1, name: 'Downtown Branch' },
              { id: 2, name: 'Mall Branch' },
              { id: 3, name: 'Airport Branch' }
            ]}
            data={sampleRevenueData}
            exportColumns={['date', 'revenue', 'profit', 'expenses']}
            exportId="revenue-chart"
            onRefresh={() => window.location.reload()}
          />
        </div>
      </section>

      {/* Line Chart Example */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Line Chart - Revenue Trends</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-6">
          {/* Custom Legend */}
          <ChartLegend
            items={legendItems}
            onItemToggle={handleLegendToggle}
            layout="horizontal"
            position="top"
            showToggleAll={true}
            className="mb-4"
          />
          
          <LineChartWrapper
            id="revenue-chart"
            data={revenueData || sampleRevenueData}
            xKey="date"
            yKeys={visibleSeries}
            showBrush={true}
            showGrid={true}
            height={400}
            loading={isLoading}
            error={error}
            onDrillDown={(data) => {
              console.log('Drill down to:', data)
              // Navigate to detailed view
            }}
            className="mt-4"
          />
        </div>
      </section>

      {/* Bar Chart Example */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Bar Chart - Category Performance</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Vertical Stacked Bars */}
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <h3 className="text-lg font-medium mb-4">Quarterly Sales by Category</h3>
            <BarChartWrapper
              data={sampleCategoryData}
              xKey="category"
              yKeys={['Q1', 'Q2', 'Q3', 'Q4']}
              stackId="quarters"
              orientation="vertical"
              showValues={false}
              height={350}
              onDrillDown={(data) => {
                console.log('Category drill-down:', data)
              }}
            />
          </div>

          {/* Horizontal Bars */}
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <h3 className="text-lg font-medium mb-4">Top Categories (Horizontal)</h3>
            <BarChartWrapper
              data={sampleCategoryData.map(item => ({
                category: item.category,
                total: item.Q1 + item.Q2 + item.Q3 + item.Q4
              }))}
              xKey="category"
              yKeys={['total']}
              orientation="horizontal"
              showValues={true}
              height={300}
            />
          </div>
        </div>
      </section>

      {/* Pie Chart Example */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Pie Chart - Product Distribution</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Regular Pie Chart */}
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <h3 className="text-lg font-medium mb-4">Sales Volume Distribution</h3>
            <PieChartWrapper
              data={sampleProductData}
              valueKey="value"
              labelKey="name"
              maxSlices={4}
              showPercentages={true}
              height={350}
              onDrillDown={(data) => {
                console.log('Product drill-down:', data)
              }}
            />
          </div>

          {/* Donut Chart */}
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <h3 className="text-lg font-medium mb-4">Revenue Distribution (Donut)</h3>
            <PieChartWrapper
              data={sampleProductData}
              valueKey="revenue"
              labelKey="name"
              innerRadius={60}
              maxSlices={5}
              showPercentages={true}
              height={350}
            />
          </div>
        </div>
      </section>

      {/* Area Chart Example */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Area Chart - Cumulative Trends</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-medium mb-4">Revenue Components Over Time</h3>
          <AreaChartWrapper
            data={sampleRevenueData}
            xKey="date"
            yKeys={['profit', 'expenses']}
            stackId="components"
            fillOpacity={0.6}
            showLegend={true}
            height={400}
            onSeriesToggle={(seriesId, visible) => {
              console.log(`Series ${seriesId} ${visible ? 'shown' : 'hidden'}`)
            }}
          />
        </div>
      </section>

      {/* Heatmap Example */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Heatmap - Sales Patterns</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-medium mb-4">Hourly Sales by Day of Week</h3>
          <HeatmapWrapper
            data={sampleHeatmapData}
            xKey="hour"
            yKey="day"
            valueKey="sales"
            colorScale={['#EBF8FF', '#3182CE']}
            showValues={true}
            height={300}
            onCellClick={(data) => {
              console.log('Heatmap cell clicked:', data)
            }}
          />
        </div>
      </section>

      {/* Cohort Retention Example */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Cohort Analysis</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-medium mb-4">Customer Retention by Signup Cohort</h3>
          <CohortRetentionChart
            cohortData={[
              { cohort: '2024-01', period: 0, retention: 100, customers: 150 },
              { cohort: '2024-01', period: 1, retention: 65, customers: 98 },
              { cohort: '2024-01', period: 2, retention: 45, customers: 68 },
              { cohort: '2024-02', period: 0, retention: 100, customers: 200 },
              { cohort: '2024-02', period: 1, retention: 70, customers: 140 }
            ]}
            cohortKey="cohort"
            periodKey="period"
            retentionKey="retention"
            height={350}
          />
        </div>
      </section>

      {/* Advanced Integration Example */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Advanced Integration</h2>
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-medium mb-4">Multi-Chart Dashboard</h3>
          
          {/* Dashboard Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {/* KPI Cards with Mini Charts */}
            <div className="space-y-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Total Revenue</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">$72,000</p>
                  </div>
                  <div className="text-green-600">+15%</div>
                </div>
                <LineChartWrapper
                  data={sampleRevenueData}
                  xKey="date"
                  yKeys={['revenue']}
                  height={60}
                  showGrid={false}
                  showLegend={false}
                  showTooltip={false}
                  className="mt-2"
                />
              </div>

              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Profit Margin</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">27.5%</p>
                  </div>
                  <div className="text-green-600">+2.3%</div>
                </div>
                <AreaChartWrapper
                  data={sampleRevenueData.map(item => ({
                    date: item.date,
                    margin: (item.profit / item.revenue) * 100
                  }))}
                  xKey="date"
                  yKeys={['margin']}
                  height={60}
                  showGrid={false}
                  showLegend={false}
                  showTooltip={false}
                  className="mt-2"
                />
              </div>
            </div>

            {/* Medium Chart */}
            <div className="lg:col-span-1">
              <h4 className="text-md font-medium mb-3">Top Products</h4>
              <PieChartWrapper
                data={sampleProductData}
                valueKey="revenue"
                labelKey="name"
                height={250}
                innerRadius={40}
                showPercentages={true}
              />
            </div>

            {/* Large Chart */}
            <div className="lg:col-span-1">
              <h4 className="text-md font-medium mb-3">Daily Pattern</h4>
              <BarChartWrapper
                data={[
                  { hour: '9 AM', sales: 25 },
                  { hour: '10 AM', sales: 45 },
                  { hour: '11 AM', sales: 65 },
                  { hour: '12 PM', sales: 85 },
                  { hour: '1 PM', sales: 70 },
                  { hour: '2 PM', sales: 55 }
                ]}
                xKey="hour"
                yKeys={['sales']}
                height={250}
                showValues={true}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Performance Tips */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Performance Best Practices</h2>
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
          <h3 className="text-lg font-medium text-yellow-800 dark:text-yellow-200 mb-3">
            Optimization Tips
          </h3>
          <ul className="space-y-2 text-yellow-700 dark:text-yellow-300">
            <li>• Use <code>maxDataPoints</code> option to enable automatic downsampling</li>
            <li>• Enable <code>serverAggregation</code> for large datasets</li>
            <li>• Memoize chart data processing with <code>useMemo</code></li>
            <li>• Limit concurrent chart renders (max 3-4 complex charts)</li>
            <li>• Use <code>react-window</code> for large legend lists</li>
            <li>• Implement proper loading states to improve perceived performance</li>
          </ul>
        </div>
      </section>
    </div>
  )
}

/**
 * Usage in Dashboard Components
 */

// Example: Revenue Dashboard Page
export function RevenueDashboard() {
  const [dateRange, setDateRange] = useState({
    startDate: '2024-01-01',
    endDate: '2024-12-31'
  })

  const { data: revenueData } = useChartData({
    endpoint: '/api/revenue',
    filters: dateRange
  })

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Revenue Analysis</h1>
        <ChartControls
          filters={dateRange}
          onFiltersChange={setDateRange}
          data={revenueData}
          exportId="revenue-dashboard"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LineChartWrapper
          data={revenueData}
          xKey="date"
          yKeys={['revenue', 'target']}
          showBrush={true}
        />
        
        <BarChartWrapper
          data={revenueData}
          xKey="month"
          yKeys={['actual', 'target']}
          orientation="vertical"
        />
      </div>
    </div>
  )
}

// Example: Product Analytics Page  
export function ProductAnalytics() {
  const [filters, setFilters] = useState({
    category: 'all',
    timeframe: 'month'
  })

  const { data: productData } = useChartData({
    endpoint: '/api/products/analytics',
    filters
  })

  return (
    <div className="space-y-6">
      <HeatmapWrapper
        data={productData}
        xKey="product"
        yKey="month"
        valueKey="sales"
        onCellClick={(data) => {
          // Navigate to product details
          window.location.href = `/products/${data.product}`
        }}
      />
    </div>
  )
}