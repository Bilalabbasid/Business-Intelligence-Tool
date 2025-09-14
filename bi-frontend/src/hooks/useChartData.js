/**
 * useChartData Hook
 * React Query hook for fetching and caching chart data with aggregation support
 */

import { useQuery, useQueries } from '@tanstack/react-query'
import { useMemo } from 'react'
import { apiClient } from '../api/client'
import { aggregateByTime, downsampleLTTB, validateChartData } from '../charts/chartUtils'

/**
 * Custom hook for fetching chart data with caching and aggregation
 * @param {Object} config - Hook configuration
 * @returns {Object} Query result with processed data
 */
export const useChartData = ({
  endpoint,
  params = {},
  aggregation = 'raw',
  downsampleThreshold = 10000,
  enabled = true,
  staleTime = 5 * 60 * 1000, // 5 minutes
  cacheTime = 10 * 60 * 1000, // 10 minutes
  refetchInterval = null,
  select = null,
  onSuccess = null,
  onError = null
}) => {
  // Create query key based on endpoint and params
  const queryKey = useMemo(() => {
    return [endpoint, { ...params, aggregation }]
  }, [endpoint, params, aggregation])

  // Determine if we should use server-side aggregation
  const useServerAggregation = aggregation !== 'raw'

  // Build request parameters
  const requestParams = useMemo(() => {
    const finalParams = { ...params }
    
    if (useServerAggregation) {
      finalParams.aggregation = aggregation
    }
    
    return finalParams
  }, [params, aggregation, useServerAggregation])

  // Data processing function
  const processData = useMemo(() => {
    return (rawData) => {
      if (!rawData || !Array.isArray(rawData)) {
        return { data: [], meta: { processed: false, downsampled: false } }
      }

      let processedData = rawData
      let wasDownsampled = false
      let wasAggregated = useServerAggregation

      // Client-side downsampling if data exceeds threshold and not server-aggregated
      if (!useServerAggregation && rawData.length > downsampleThreshold) {
        processedData = downsampleLTTB(rawData, downsampleThreshold)
        wasDownsampled = true
      }

      return {
        data: processedData,
        meta: {
          originalLength: rawData.length,
          processedLength: processedData.length,
          processed: wasDownsampled || wasAggregated,
          downsampled: wasDownsampled,
          aggregated: wasAggregated,
          aggregationType: aggregation
        }
      }
    }
  }, [downsampleThreshold, useServerAggregation, aggregation])

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      const response = await apiClient.get(endpoint, { params: requestParams })
      return response.data
    },
    enabled,
    staleTime,
    cacheTime,
    refetchInterval,
    select: select ? (data) => select(processData(data)) : processData,
    onSuccess: (data) => {
      // Log performance information
      if (data.meta.processed) {
        console.log(`Chart data processed: ${data.meta.originalLength} → ${data.meta.processedLength} points`)
      }
      onSuccess?.(data)
    },
    onError: (error) => {
      console.error('Chart data fetch error:', error)
      onError?.(error)
    },
    retry: (failureCount, error) => {
      // Don't retry on 4xx errors
      if (error.response?.status >= 400 && error.response?.status < 500) {
        return false
      }
      return failureCount < 3
    }
  })

  return {
    ...query,
    // Additional utility methods
    isProcessed: query.data?.meta?.processed || false,
    isDownsampled: query.data?.meta?.downsampled || false,
    isAggregated: query.data?.meta?.aggregated || false,
    originalLength: query.data?.meta?.originalLength || 0,
    processedLength: query.data?.meta?.processedLength || 0
  }
}

/**
 * Hook for fetching multiple chart datasets
 * @param {Array} queries - Array of query configurations
 * @returns {Array} Array of query results
 */
export const useMultipleChartData = (queries) => {
  return useQueries({
    queries: queries.map(queryConfig => ({
      queryKey: [queryConfig.endpoint, { ...queryConfig.params, aggregation: queryConfig.aggregation || 'raw' }],
      queryFn: async () => {
        const response = await apiClient.get(queryConfig.endpoint, { 
          params: { ...queryConfig.params, aggregation: queryConfig.aggregation || 'raw' }
        })
        return response.data
      },
      enabled: queryConfig.enabled !== false,
      staleTime: queryConfig.staleTime || 5 * 60 * 1000,
      cacheTime: queryConfig.cacheTime || 10 * 60 * 1000,
      select: queryConfig.select
    }))
  })
}

/**
 * Hook for real-time chart data with WebSocket support
 * @param {Object} config - Configuration object
 * @returns {Object} Query result with real-time data
 */
export const useRealTimeChartData = ({
  endpoint,
  params = {},
  wsEndpoint = null,
  bufferSize = 1000,
  enabled = true
}) => {
  // Use regular query for initial data
  const baseQuery = useChartData({
    endpoint,
    params,
    enabled,
    refetchInterval: wsEndpoint ? false : 30000 // Only poll if no WebSocket
  })

  // TODO: Implement WebSocket connection for real-time updates
  // This would maintain a buffer of recent data points and merge with cached data
  
  return baseQuery
}

/**
 * Hook for KPI data fetching
 * @param {Object} config - Configuration object
 * @returns {Object} Query result with KPI metrics
 */
export const useKPIData = ({
  endpoint = '/api/kpis',
  branchId = null,
  startDate = null,
  endDate = null,
  aggregation = 'day',
  enabled = true
}) => {
  const params = useMemo(() => {
    const p = { aggregation }
    if (branchId) p.branch_id = branchId
    if (startDate) p.start_date = startDate
    if (endDate) p.end_date = endDate
    return p
  }, [branchId, startDate, endDate, aggregation])

  return useChartData({
    endpoint,
    params,
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes for KPIs
    select: (data) => {
      // Process KPI data into a more consumable format
      if (!data.data || !Array.isArray(data.data)) {
        return { kpis: [], meta: data.meta }
      }

      return {
        kpis: data.data,
        meta: data.meta
      }
    }
  })
}

/**
 * Hook for dashboard summary data
 * @param {string} role - User role (super_admin, manager, analyst, staff)
 * @param {string} branchId - Branch ID (optional)
 * @returns {Object} Query result with dashboard data
 */
export const useDashboardData = (role, branchId = null) => {
  const endpoint = `/api/dashboard/${role.replace('_', '-')}/`
  
  const params = useMemo(() => {
    const p = {}
    if (branchId) p.branch_id = branchId
    return p
  }, [branchId])

  return useChartData({
    endpoint,
    params,
    staleTime: 5 * 60 * 1000, // 5 minutes for dashboard data
    select: (data) => {
      // Validate and structure dashboard data
      const validation = validateChartData(data.data || [], [])
      
      if (!validation.valid && data.data?.length > 0) {
        console.warn('Dashboard data validation failed:', validation.error)
      }

      return {
        ...data,
        summary: data.data?.summary || {},
        kpis: data.data?.kpis || [],
        charts: data.data?.charts || {}
      }
    }
  })
}

/**
 * Hook for aggregated sales data
 * @param {Object} config - Configuration object
 * @returns {Object} Query result with sales data
 */
export const useSalesData = ({
  branchId = null,
  startDate = null,
  endDate = null,
  groupBy = 'day',
  metrics = ['total_amount', 'count'],
  enabled = true
}) => {
  const params = useMemo(() => {
    const p = { group_by: groupBy, metrics: metrics.join(',') }
    if (branchId) p.branch_id = branchId
    if (startDate) p.start_date = startDate
    if (endDate) p.end_date = endDate
    return p
  }, [branchId, startDate, endDate, groupBy, metrics])

  return useChartData({
    endpoint: '/api/sales/aggregate',
    params,
    enabled,
    downsampleThreshold: 5000, // Lower threshold for sales data
    select: (data) => {
      return {
        ...data,
        data: data.data?.map(item => ({
          ...item,
          date: item.date || item.timestamp,
          // Ensure numeric values
          total_amount: Number(item.total_amount || 0),
          count: Number(item.count || 0)
        })) || []
      }
    }
  })
}

/**
 * Hook for inventory trends
 * @param {Object} config - Configuration object
 * @returns {Object} Query result with inventory data
 */
export const useInventoryData = ({
  branchId = null,
  startDate = null,
  endDate = null,
  itemId = null,
  enabled = true
}) => {
  const params = useMemo(() => {
    const p = {}
    if (branchId) p.branch_id = branchId
    if (startDate) p.start_date = startDate
    if (endDate) p.end_date = endDate
    if (itemId) p.item_id = itemId
    return p
  }, [branchId, startDate, endDate, itemId])

  return useChartData({
    endpoint: '/api/inventory/trends',
    params,
    enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes for inventory
    select: (data) => {
      return {
        ...data,
        data: data.data?.map(item => ({
          ...item,
          stock_level: Number(item.stock_level || 0),
          reorder_point: Number(item.reorder_point || 0)
        })) || []
      }
    }
  })
}

// Export utility for invalidating chart data cache
export const chartDataUtils = {
  /**
   * Invalidate specific chart data
   * @param {Object} queryClient - React Query client
   * @param {string} endpoint - Endpoint to invalidate
   * @param {Object} params - Parameters to match
   */
  invalidateChartData: (queryClient, endpoint, params = {}) => {
    queryClient.invalidateQueries([endpoint, params])
  },

  /**
   * Prefetch chart data
   * @param {Object} queryClient - React Query client
   * @param {string} endpoint - Endpoint to prefetch
   * @param {Object} params - Parameters for the request
   */
  prefetchChartData: (queryClient, endpoint, params = {}) => {
    queryClient.prefetchQuery([endpoint, params], async () => {
      const response = await apiClient.get(endpoint, { params })
      return response.data
    })
  },

  /**
   * Clear all chart data cache
   * @param {Object} queryClient - React Query client
   */
  clearChartCache: (queryClient) => {
    queryClient.removeQueries(['api'])
  }
}