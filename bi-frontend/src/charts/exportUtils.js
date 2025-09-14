/**
 * Export Utilities
 * Functions for exporting charts and data in various formats
 */

import html2canvas from 'html2canvas'

/**
 * Export chart as PNG image
 * @param {string} exportId - Element ID of the chart container
 * @param {string} filename - Output filename
 * @param {Object} options - Export options
 */
export const exportChartPNG = async (exportId, filename = 'chart.png', options = {}) => {
  try {
    const element = document.getElementById(exportId)
    if (!element) {
      throw new Error(`Element with ID "${exportId}" not found`)
    }

    const {
      backgroundColor = '#ffffff',
      scale = 2,
      quality = 0.95,
      width = null,
      height = null
    } = options

    const canvas = await html2canvas(element, {
      backgroundColor,
      scale,
      width,
      height,
      useCORS: true,
      allowTaint: true,
      logging: false
    })

    // Create download link
    const link = document.createElement('a')
    link.download = filename
    link.href = canvas.toDataURL('image/png', quality)
    
    // Trigger download
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    return { success: true, message: 'Chart exported successfully' }
  } catch (error) {
    console.error('Error exporting chart as PNG:', error)
    return { success: false, error: error.message }
  }
}

/**
 * Export chart as SVG (if chart is SVG-based)
 * @param {string} exportId - Element ID of the chart container
 * @param {string} filename - Output filename
 */
export const exportChartSVG = (exportId, filename = 'chart.svg') => {
  try {
    const element = document.getElementById(exportId)
    if (!element) {
      throw new Error(`Element with ID "${exportId}" not found`)
    }

    const svgElement = element.querySelector('svg')
    if (!svgElement) {
      throw new Error('No SVG element found in the chart container')
    }

    // Clone the SVG to avoid modifying the original
    const clonedSvg = svgElement.cloneNode(true)
    
    // Add XML namespace if not present
    if (!clonedSvg.getAttribute('xmlns')) {
      clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
    }

    // Create blob and download
    const svgData = new XMLSerializer().serializeToString(clonedSvg)
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    
    const link = document.createElement('a')
    link.download = filename
    link.href = URL.createObjectURL(blob)
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(link.href)

    return { success: true, message: 'Chart exported successfully' }
  } catch (error) {
    console.error('Error exporting chart as SVG:', error)
    return { success: false, error: error.message }
  }
}

/**
 * Export data as CSV
 * @param {Array} data - Array of objects to export
 * @param {Array} columns - Column definitions with key and label
 * @param {string} filename - Output filename
 */
export const exportTableCSV = (data, columns, filename = 'data.csv') => {
  try {
    if (!Array.isArray(data) || data.length === 0) {
      throw new Error('No data to export')
    }

    if (!Array.isArray(columns) || columns.length === 0) {
      throw new Error('No columns defined for export')
    }

    // Create CSV header
    const headers = columns.map(col => `"${col.label || col.key}"`)
    const csvContent = [headers.join(',')]

    // Add data rows
    data.forEach(row => {
      const values = columns.map(col => {
        const value = row[col.key]
        
        // Handle different data types
        if (value === null || value === undefined) {
          return '""'
        } else if (typeof value === 'string') {
          // Escape quotes in strings
          return `"${value.replace(/"/g, '""')}"`
        } else if (value instanceof Date) {
          return `"${value.toISOString()}"`
        } else {
          return `"${value}"`
        }
      })
      
      csvContent.push(values.join(','))
    })

    // Create and download file
    const csvString = csvContent.join('\n')
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' })
    
    const link = document.createElement('a')
    link.download = filename
    link.href = URL.createObjectURL(blob)
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(link.href)

    return { success: true, message: 'Data exported successfully' }
  } catch (error) {
    console.error('Error exporting CSV:', error)
    return { success: false, error: error.message }
  }
}

/**
 * Export chart data in multiple formats
 * @param {string} exportId - Element ID for image export
 * @param {Array} data - Data for CSV export
 * @param {Array} columns - Columns for CSV export
 * @param {string} baseFilename - Base filename (extension will be added)
 * @param {Array} formats - Array of formats to export ['png', 'svg', 'csv']
 */
export const exportMultipleFormats = async (
  exportId, 
  data, 
  columns, 
  baseFilename = 'chart',
  formats = ['png', 'csv']
) => {
  const results = []

  for (const format of formats) {
    try {
      let result
      switch (format.toLowerCase()) {
        case 'png':
          result = await exportChartPNG(exportId, `${baseFilename}.png`)
          break
        case 'svg':
          result = exportChartSVG(exportId, `${baseFilename}.svg`)
          break
        case 'csv':
          result = exportTableCSV(data, columns, `${baseFilename}.csv`)
          break
        default:
          result = { success: false, error: `Unsupported format: ${format}` }
      }
      
      results.push({ format, ...result })
    } catch (error) {
      results.push({ format, success: false, error: error.message })
    }
  }

  return results
}

/**
 * Generate shareable permalink for chart configuration
 * @param {Object} chartConfig - Chart configuration object
 * @param {string} baseUrl - Base URL for the application
 */
export const generatePermalink = (chartConfig, baseUrl = window.location.origin) => {
  try {
    const params = new URLSearchParams()
    
    // Add chart configuration as compressed JSON
    const configString = JSON.stringify(chartConfig)
    const encodedConfig = btoa(configString)
    params.set('config', encodedConfig)
    
    const permalink = `${baseUrl}${window.location.pathname}?${params.toString()}`
    
    return { success: true, permalink }
  } catch (error) {
    console.error('Error generating permalink:', error)
    return { success: false, error: error.message }
  }
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
export const copyToClipboard = async (text) => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.opacity = '0'
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
    }
    
    return { success: true, message: 'Copied to clipboard' }
  } catch (error) {
    console.error('Error copying to clipboard:', error)
    return { success: false, error: error.message }
  }
}

/**
 * Server-side export utilities for large datasets
 */
export const serverExportUtils = {
  /**
   * Request server-side CSV export
   * @param {string} endpoint - Export endpoint URL
   * @param {Object} params - Export parameters
   */
  requestCSVExport: async (endpoint, params = {}) => {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}` // Adjust based on auth implementation
        },
        body: JSON.stringify(params)
      })

      if (!response.ok) {
        throw new Error(`Export request failed: ${response.statusText}`)
      }

      const result = await response.json()
      
      if (result.downloadUrl) {
        // Direct download
        const link = document.createElement('a')
        link.href = result.downloadUrl
        link.download = result.filename || 'export.csv'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }

      return { success: true, jobId: result.jobId, message: result.message }
    } catch (error) {
      console.error('Error requesting server export:', error)
      return { success: false, error: error.message }
    }
  },

  /**
   * Poll export job status
   * @param {string} jobId - Export job ID
   * @param {string} statusEndpoint - Status check endpoint
   */
  pollExportStatus: async (jobId, statusEndpoint) => {
    try {
      const response = await fetch(`${statusEndpoint}/${jobId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (!response.ok) {
        throw new Error(`Status check failed: ${response.statusText}`)
      }

      const status = await response.json()
      return { success: true, status }
    } catch (error) {
      console.error('Error checking export status:', error)
      return { success: false, error: error.message }
    }
  }
}

/**
 * Utility to show export notifications
 * @param {Object} result - Export result
 * @param {Function} showToast - Toast notification function
 */
export const handleExportResult = (result, showToast) => {
  if (result.success) {
    showToast?.({
      type: 'success',
      message: result.message || 'Export completed successfully'
    })
  } else {
    showToast?.({
      type: 'error',
      message: result.error || 'Export failed'
    })
  }
}

// Export format configurations
export const exportFormats = {
  png: {
    label: 'PNG Image',
    extension: '.png',
    mimeType: 'image/png',
    description: 'High-quality image suitable for presentations and documents'
  },
  svg: {
    label: 'SVG Vector',
    extension: '.svg',
    mimeType: 'image/svg+xml',
    description: 'Scalable vector format perfect for web and print'
  },
  csv: {
    label: 'CSV Data',
    extension: '.csv',
    mimeType: 'text/csv',
    description: 'Raw data in comma-separated values format'
  },
  pdf: {
    label: 'PDF Document',
    extension: '.pdf',
    mimeType: 'application/pdf',
    description: 'Professional document format with charts and data'
  }
}