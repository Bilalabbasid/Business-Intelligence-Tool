/**
 * Chart Visual Tokens
 * Centralized design tokens for consistent chart styling
 */

export const chartTokens = {
  // Color palettes
  colors: {
    // Primary color palette (colorblind safe)
    primary: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'],
    
    // Semantic colors
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    
    // Neutral colors
    neutral: {
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      300: '#d1d5db',
      400: '#9ca3af',
      500: '#6b7280',
      600: '#4b5563',
      700: '#374151',
      800: '#1f2937',
      900: '#111827',
    },
    
    // Gradient colors for heatmaps
    heatmap: {
      low: '#dbeafe',
      medium: '#60a5fa',
      high: '#1d4ed8',
      intense: '#1e3a8a'
    },
    
    // Pattern fills for accessibility
    patterns: {
      dots: 'url(#dots)',
      stripes: 'url(#stripes)',
      crosses: 'url(#crosses)'
    }
  },
  
  // Typography
  typography: {
    fontFamily: {
      primary: 'Inter, system-ui, -apple-system, sans-serif',
      mono: 'JetBrains Mono, Monaco, Consolas, monospace'
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem'
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    }
  },
  
  // Spacing
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
    '2xl': '2rem',
    '3xl': '3rem'
  },
  
  // Chart dimensions
  dimensions: {
    height: {
      small: 200,
      medium: 300,
      large: 400,
      xlarge: 500
    },
    margin: {
      tight: { top: 5, right: 5, bottom: 5, left: 5 },
      normal: { top: 20, right: 30, bottom: 20, left: 40 },
      loose: { top: 30, right: 50, bottom: 30, left: 60 }
    }
  },
  
  // Animation
  animation: {
    duration: {
      fast: 150,
      normal: 300,
      slow: 500
    },
    easing: {
      ease: 'ease',
      easeIn: 'ease-in',
      easeOut: 'ease-out',
      easeInOut: 'ease-in-out'
    }
  },
  
  // Chart-specific tokens
  chart: {
    strokeWidth: {
      thin: 1,
      normal: 2,
      thick: 3
    },
    borderRadius: {
      none: 0,
      small: 2,
      medium: 4,
      large: 8
    },
    opacity: {
      hover: 0.8,
      disabled: 0.4,
      background: 0.1
    }
  }
}

// Theme variants
export const darkTheme = {
  ...chartTokens,
  colors: {
    ...chartTokens.colors,
    neutral: {
      50: '#111827',
      100: '#1f2937',
      200: '#374151',
      300: '#4b5563',
      400: '#6b7280',
      500: '#9ca3af',
      600: '#d1d5db',
      700: '#e5e7eb',
      800: '#f3f4f6',
      900: '#f9fafb',
    }
  }
}

// Utility functions
export const getColorByIndex = (index, palette = chartTokens.colors.primary) => {
  return palette[index % palette.length]
}

export const getContrastColor = (backgroundColor) => {
  // Simple contrast calculation
  const hex = backgroundColor.replace('#', '')
  const r = parseInt(hex.substr(0, 2), 16)
  const g = parseInt(hex.substr(2, 2), 16)
  const b = parseInt(hex.substr(4, 2), 16)
  const brightness = ((r * 299) + (g * 587) + (b * 114)) / 1000
  return brightness > 125 ? chartTokens.colors.neutral[900] : chartTokens.colors.neutral[50]
}

export const createGradient = (id, colors) => (
  `<defs>
    <linearGradient id="${id}" x1="0%" y1="0%" x2="0%" y2="100%">
      ${colors.map((color, index) => 
        `<stop offset="${(index / (colors.length - 1)) * 100}%" stopColor="${color}" />`
      ).join('')}
    </linearGradient>
  </defs>`
)