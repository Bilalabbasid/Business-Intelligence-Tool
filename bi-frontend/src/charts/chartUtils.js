/**
 * Chart Utilities
 * Helper functions for data formatting, downsampling, and aggregation
 */

// Number formatting utilities
export const formatNumber = (value, options = {}) => {
  if (value === null || value === undefined) return 'N/A'
  
  const {
    precision = 0,
    prefix = '',
    suffix = '',
    compact = false,
    currency = false,
    percentage = false
  } = options

  let formatted = value

  // Handle percentage
  if (percentage) {
    formatted = (value * 100).toFixed(precision)
    return `${prefix}${formatted}%${suffix}`
  }

  // Handle currency
  if (currency) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    }).format(value)
  }

  // Handle compact notation
  if (compact) {
    const formatter = new Intl.NumberFormat('en-US', {
      notation: 'compact',
      compactDisplay: 'short',
      minimumFractionDigits: 0,
      maximumFractionDigits: 1,
    })
    formatted = formatter.format(value)
  } else {
    formatted = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    }).format(value)
  }

  return `${prefix}${formatted}${suffix}`
}

// Date formatting utilities
export const formatDate = (date, format = 'short') => {
  if (!date) return 'N/A'
  
  const d = new Date(date)
  if (isNaN(d.getTime())) return 'Invalid Date'

  const formats = {
    short: { month: 'short', day: 'numeric' },
    medium: { month: 'short', day: 'numeric', year: 'numeric' },
    long: { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' },
    time: { hour: '2-digit', minute: '2-digit' },
    datetime: { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
  }

  return d.toLocaleDateString('en-US', formats[format] || formats.medium)
}

// Percentage change calculation
export const calculatePercentageChange = (current, previous) => {
  if (!previous || previous === 0) return null
  return ((current - previous) / previous) * 100
}

// Largest-Triangle-Three-Buckets (LTTB) downsampling algorithm
export const downsampleLTTB = (data, threshold, xAccessor = 'x', yAccessor = 'y') => {
  if (data.length <= threshold) return data
  if (threshold <= 2) return [data[0], data[data.length - 1]]

  const sampled = []
  const bucketSize = (data.length - 2) / (threshold - 2)

  // Always include first point
  sampled.push(data[0])

  let bucketIndex = 0
  for (let i = 1; i < threshold - 1; i++) {
    const bucketStart = Math.floor(i * bucketSize) + 1
    const bucketEnd = Math.floor((i + 1) * bucketSize) + 1
    const bucketRange = Math.min(bucketEnd, data.length - 1) - bucketStart

    // Calculate average point of next bucket for triangle area calculation
    let avgX = 0
    let avgY = 0
    const nextBucketStart = bucketEnd
    const nextBucketEnd = Math.min(Math.floor((i + 2) * bucketSize) + 1, data.length - 1)

    for (let j = nextBucketStart; j < nextBucketEnd; j++) {
      avgX += data[j][xAccessor] || 0
      avgY += data[j][yAccessor] || 0
    }
    avgX /= (nextBucketEnd - nextBucketStart)
    avgY /= (nextBucketEnd - nextBucketStart)

    // Find point with largest triangle area
    let maxArea = -1
    let maxIndex = bucketStart

    const prevX = sampled[sampled.length - 1][xAccessor] || 0
    const prevY = sampled[sampled.length - 1][yAccessor] || 0

    for (let j = bucketStart; j < bucketEnd; j++) {
      const currX = data[j][xAccessor] || 0
      const currY = data[j][yAccessor] || 0

      // Calculate triangle area
      const area = Math.abs(
        (prevX - avgX) * (currY - prevY) - (prevX - currX) * (avgY - prevY)
      )

      if (area > maxArea) {
        maxArea = area
        maxIndex = j
      }
    }

    sampled.push(data[maxIndex])
  }

  // Always include last point
  sampled.push(data[data.length - 1])

  return sampled
}

// Data aggregation utilities
export const aggregateByTime = (data, timeKey, valueKey, aggregation = 'sum', groupBy = 'day') => {
  const groupedData = {}

  data.forEach(item => {
    const date = new Date(item[timeKey])
    let key

    switch (groupBy) {
      case 'hour':
        key = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}-${date.getHours()}`
        break
      case 'day':
        key = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
        break
      case 'week':
        const weekStart = new Date(date)
        weekStart.setDate(date.getDate() - date.getDay())
        key = `${weekStart.getFullYear()}-${weekStart.getMonth()}-${weekStart.getDate()}`
        break
      case 'month':
        key = `${date.getFullYear()}-${date.getMonth()}`
        break
      default:
        key = item[timeKey]
    }

    if (!groupedData[key]) {
      groupedData[key] = {
        [timeKey]: key,
        values: [],
        count: 0
      }
    }

    groupedData[key].values.push(item[valueKey])
    groupedData[key].count++
  })

  return Object.values(groupedData).map(group => {
    let aggregatedValue

    switch (aggregation) {
      case 'sum':
        aggregatedValue = group.values.reduce((sum, val) => sum + val, 0)
        break
      case 'avg':
        aggregatedValue = group.values.reduce((sum, val) => sum + val, 0) / group.values.length
        break
      case 'max':
        aggregatedValue = Math.max(...group.values)
        break
      case 'min':
        aggregatedValue = Math.min(...group.values)
        break
      case 'count':
        aggregatedValue = group.count
        break
      default:
        aggregatedValue = group.values[0]
    }

    return {
      [timeKey]: group[timeKey],
      [valueKey]: aggregatedValue,
      count: group.count
    }
  })
}

// Calculate moving average
export const calculateMovingAverage = (data, windowSize, valueKey) => {
  return data.map((item, index) => {
    const start = Math.max(0, index - Math.floor(windowSize / 2))
    const end = Math.min(data.length, index + Math.ceil(windowSize / 2))
    const window = data.slice(start, end)
    const average = window.reduce((sum, item) => sum + item[valueKey], 0) / window.length

    return {
      ...item,
      [`${valueKey}_ma`]: average
    }
  })
}

// Find outliers using IQR method
export const findOutliers = (data, valueKey) => {
  const values = data.map(item => item[valueKey]).sort((a, b) => a - b)
  const q1Index = Math.floor(values.length * 0.25)
  const q3Index = Math.floor(values.length * 0.75)
  const q1 = values[q1Index]
  const q3 = values[q3Index]
  const iqr = q3 - q1
  const lowerBound = q1 - 1.5 * iqr
  const upperBound = q3 + 1.5 * iqr

  return data.filter(item => {
    const value = item[valueKey]
    return value < lowerBound || value > upperBound
  })
}

// Generate time series data for given range
export const generateTimeRange = (startDate, endDate, interval = 'day') => {
  const dates = []
  const current = new Date(startDate)
  const end = new Date(endDate)

  while (current <= end) {
    dates.push(new Date(current))
    
    switch (interval) {
      case 'hour':
        current.setHours(current.getHours() + 1)
        break
      case 'day':
        current.setDate(current.getDate() + 1)
        break
      case 'week':
        current.setDate(current.getDate() + 7)
        break
      case 'month':
        current.setMonth(current.getMonth() + 1)
        break
    }
  }

  return dates
}

// Debounce utility for performance
export const debounce = (func, wait) => {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// Performance monitoring
export const measurePerformance = (label, fn) => {
  const start = performance.now()
  const result = fn()
  const end = performance.now()
  console.log(`${label}: ${(end - start).toFixed(2)}ms`)
  return result
}

// Data validation utilities
export const validateChartData = (data, requiredKeys = []) => {
  if (!Array.isArray(data)) {
    return { valid: false, error: 'Data must be an array' }
  }

  if (data.length === 0) {
    return { valid: false, error: 'Data array is empty' }
  }

  for (const key of requiredKeys) {
    if (!data.every(item => key in item)) {
      return { valid: false, error: `Missing required key: ${key}` }
    }
  }

  return { valid: true }
}

// Color utilities
export const interpolateColor = (color1, color2, factor) => {
  const hex1 = color1.replace('#', '')
  const hex2 = color2.replace('#', '')
  
  const r1 = parseInt(hex1.substr(0, 2), 16)
  const g1 = parseInt(hex1.substr(2, 2), 16)
  const b1 = parseInt(hex1.substr(4, 2), 16)
  
  const r2 = parseInt(hex2.substr(0, 2), 16)
  const g2 = parseInt(hex2.substr(2, 2), 16)
  const b2 = parseInt(hex2.substr(4, 2), 16)
  
  const r = Math.round(r1 + (r2 - r1) * factor)
  const g = Math.round(g1 + (g2 - g1) * factor)
  const b = Math.round(b1 + (b2 - b1) * factor)
  
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
}