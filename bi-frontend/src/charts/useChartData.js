import { useState, useEffect } from 'react'
import axios from 'axios'

// Hook to retrieve cohort data from backend or provide demo data
export function useChartData(endpoint = '/api/analytics/cohort/') {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        const res = await axios.get(endpoint)
        if (!cancelled) setData(res.data)
      } catch (err) {
        // fallback demo shaped data
        if (!cancelled) setData(null)
        setError(err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [endpoint])

  return { loading, data, error }
}

// Provide a default export for compatibility
export default useChartData
