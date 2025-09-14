import { useQuery } from '@tanstack/react-query'
import {
  Building2,
  Users,
  ShoppingCart,
  TrendingUp,
  DollarSign,
  Package
} from 'lucide-react'
import { KpiCard, KpiGrid } from '../../components/kpi'
import { LineChartComponent, BarChartComponent, PieChartComponent } from '../../components/charts'
import { apiClient } from '../../api/client'

export default function SuperAdminDashboard() {
  // Fetch dashboard data
  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['super-admin-dashboard'],
    queryFn: () => apiClient.get('/api/dashboard/super-admin/'),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Mock data for development
  const mockKpiData = {
    totalRevenue: { value: 1250000, previousValue: 1180000 },
    totalBranches: { value: 15, previousValue: 14 },
    totalUsers: { value: 248, previousValue: 235 },
    totalSales: { value: 3567, previousValue: 3289 }
  }

  const mockSalesData = [
    { name: 'Jan', sales: 4000, revenue: 2400 },
    { name: 'Feb', sales: 3000, revenue: 1398 },
    { name: 'Mar', sales: 2000, revenue: 9800 },
    { name: 'Apr', sales: 2780, revenue: 3908 },
    { name: 'May', sales: 1890, revenue: 4800 },
    { name: 'Jun', sales: 2390, revenue: 3800 },
  ]

  const mockBranchData = [
    { name: 'Branch A', sales: 4000 },
    { name: 'Branch B', sales: 3000 },
    { name: 'Branch C', sales: 2000 },
    { name: 'Branch D', sales: 2780 },
    { name: 'Branch E', sales: 1890 },
  ]

  const mockCategoryData = [
    { name: 'Electronics', value: 35 },
    { name: 'Clothing', value: 25 },
    { name: 'Food & Beverage', value: 20 },
    { name: 'Books', value: 15 },
    { name: 'Sports', value: 5 },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Super Admin Dashboard
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Overview of all branches and business performance
        </p>
      </div>

      {/* KPI Cards */}
      <KpiGrid columns={{ sm: 1, md: 2, lg: 4 }}>
        <KpiCard
          title="Total Revenue"
          value={mockKpiData.totalRevenue.value}
          previousValue={mockKpiData.totalRevenue.previousValue}
          format="currency"
          icon={DollarSign}
          isLoading={isLoading}
          subtitle="This month"
        />
        <KpiCard
          title="Total Branches"
          value={mockKpiData.totalBranches.value}
          previousValue={mockKpiData.totalBranches.previousValue}
          icon={Building2}
          isLoading={isLoading}
          subtitle="Active branches"
        />
        <KpiCard
          title="Total Users"
          value={mockKpiData.totalUsers.value}
          previousValue={mockKpiData.totalUsers.previousValue}
          icon={Users}
          isLoading={isLoading}
          subtitle="All branches"
        />
        <KpiCard
          title="Total Sales"
          value={mockKpiData.totalSales.value}
          previousValue={mockKpiData.totalSales.previousValue}
          icon={ShoppingCart}
          isLoading={isLoading}
          subtitle="This month"
        />
      </KpiGrid>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sales Trend */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Sales & Revenue Trend
          </h3>
          <LineChartComponent
            data={mockSalesData}
            lines={[
              { dataKey: 'sales', name: 'Sales', color: '#3b82f6' },
              { dataKey: 'revenue', name: 'Revenue', color: '#10b981' }
            ]}
            height={300}
            isLoading={isLoading}
          />
        </div>

        {/* Branch Performance */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Branch Performance
          </h3>
          <BarChartComponent
            data={mockBranchData}
            bars={[{ dataKey: 'sales', name: 'Sales' }]}
            height={300}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Additional Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sales by Category */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Sales by Category
          </h3>
          <PieChartComponent
            data={mockCategoryData}
            height={250}
            isLoading={isLoading}
          />
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Recent Activity
          </h3>
          <div className="space-y-4">
            {[
              { action: 'New branch opened in Downtown', time: '2 hours ago', type: 'success' },
              { action: 'Monthly report generated', time: '4 hours ago', type: 'info' },
              { action: 'System maintenance completed', time: '6 hours ago', type: 'success' },
              { action: 'User permission updated', time: '8 hours ago', type: 'warning' },
            ].map((activity, index) => (
              <div key={index} className="flex items-center space-x-3">
                <div className={`w-2 h-2 rounded-full ${
                  activity.type === 'success' ? 'bg-green-400' :
                  activity.type === 'warning' ? 'bg-yellow-400' :
                  activity.type === 'error' ? 'bg-red-400' : 'bg-blue-400'
                }`}></div>
                <div className="flex-1">
                  <p className="text-sm text-gray-900 dark:text-white">{activity.action}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}