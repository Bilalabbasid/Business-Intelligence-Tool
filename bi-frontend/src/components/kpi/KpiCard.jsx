import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '../../utils'

export default function KpiCard({
  title,
  value,
  previousValue,
  unit = '',
  format = 'number',
  className = '',
  isLoading = false,
  icon: Icon,
  trend = 'neutral',
  subtitle
}) {
  // Calculate percentage change
  const calculateChange = () => {
    if (!previousValue || previousValue === 0) return null
    const change = ((value - previousValue) / previousValue) * 100
    return change
  }

  // Format the display value
  const formatValue = (val) => {
    if (isLoading) return '---'
    
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(val)
      case 'percentage':
        return `${val.toFixed(1)}%`
      case 'decimal':
        return val.toFixed(2)
      default:
        return new Intl.NumberFormat('en-US').format(val)
    }
  }

  const change = calculateChange()
  const isPositive = change > 0
  const isNegative = change < 0

  // Determine trend icon and color
  const getTrendIcon = () => {
    if (trend === 'up' || (change !== null && isPositive)) {
      return <TrendingUp className="h-4 w-4" />
    }
    if (trend === 'down' || (change !== null && isNegative)) {
      return <TrendingDown className="h-4 w-4" />
    }
    return <Minus className="h-4 w-4" />
  }

  const getTrendColor = () => {
    if (trend === 'up' || (change !== null && isPositive)) {
      return 'text-green-600 dark:text-green-400'
    }
    if (trend === 'down' || (change !== null && isNegative)) {
      return 'text-red-600 dark:text-red-400'
    }
    return 'text-gray-500 dark:text-gray-400'
  }

  return (
    <div className={cn(
      'bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg border border-gray-200 dark:border-gray-700',
      className
    )}>
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            {Icon && (
              <Icon className="h-6 w-6 text-gray-400 dark:text-gray-500" />
            )}
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                {title}
              </dt>
              <dd className="flex items-baseline">
                <div className={cn(
                  'text-2xl font-semibold text-gray-900 dark:text-white',
                  isLoading && 'animate-pulse'
                )}>
                  {formatValue(value)}{unit}
                </div>
                {change !== null && (
                  <div className={cn(
                    'ml-2 flex items-baseline text-sm font-semibold',
                    getTrendColor()
                  )}>
                    {getTrendIcon()}
                    <span className="sr-only">
                      {isPositive ? 'Increased' : isNegative ? 'Decreased' : 'No change'} by
                    </span>
                    {Math.abs(change).toFixed(1)}%
                  </div>
                )}
              </dd>
              {subtitle && (
                <dd className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {subtitle}
                </dd>
              )}
            </dl>
          </div>
        </div>
      </div>
      
      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-white dark:bg-gray-800 bg-opacity-50 flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
        </div>
      )}
    </div>
  )
}