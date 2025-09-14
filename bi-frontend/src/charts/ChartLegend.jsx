/**
 * ChartLegend Component
 * Reusable legend with toggles, keyboard navigation, and consistent styling
 */

import React, { useState, useCallback, useRef, useEffect } from 'react'
import { cn } from '../utils'
import { chartTokens } from './chart-tokens'
import { Eye, EyeOff, Square } from 'lucide-react'

/**
 * ChartLegend Component
 * @param {Object} props - Component props
 * @param {Array} props.items - Legend items [{id, label, color, visible, disabled}]
 * @param {Function} props.onItemToggle - Toggle handler (id, visible) => void
 * @param {string} props.layout - 'horizontal' or 'vertical'
 * @param {string} props.position - 'top', 'bottom', 'left', 'right'
 * @param {boolean} props.showToggleAll - Show toggle all button
 * @param {boolean} props.showSymbols - Show color symbols
 * @param {string} props.symbolType - 'square', 'circle', 'line'
 * @param {string} props.size - 'sm', 'md', 'lg'
 * @param {boolean} props.interactive - Allow interactions
 * @param {string} props.className - CSS class name
 */
export default function ChartLegend({
  items = [],
  onItemToggle = () => {},
  layout = 'horizontal',
  position = 'bottom',
  showToggleAll = false,
  showSymbols = true,
  symbolType = 'square',
  size = 'md',
  interactive = true,
  className = ''
}) {
  const [focusedIndex, setFocusedIndex] = useState(-1)
  const legendRef = useRef(null)
  const itemRefs = useRef([])

  // Size configurations
  const sizeConfig = {
    sm: {
      text: 'text-xs',
      symbol: 'w-3 h-3',
      padding: 'p-1',
      gap: 'gap-2'
    },
    md: {
      text: 'text-sm',
      symbol: 'w-4 h-4',
      padding: 'p-2',
      gap: 'gap-3'
    },
    lg: {
      text: 'text-base',
      symbol: 'w-5 h-5',
      padding: 'p-3',
      gap: 'gap-4'
    }
  }

  const config = sizeConfig[size] || sizeConfig.md

  // Handle keyboard navigation
  const handleKeyDown = useCallback((event) => {
    if (!interactive || items.length === 0) return

    switch (event.key) {
      case 'ArrowRight':
      case 'ArrowDown':
        event.preventDefault()
        setFocusedIndex(prev => {
          const next = prev < items.length - 1 ? prev + 1 : 0
          itemRefs.current[next]?.focus()
          return next
        })
        break
      
      case 'ArrowLeft':
      case 'ArrowUp':
        event.preventDefault()
        setFocusedIndex(prev => {
          const next = prev > 0 ? prev - 1 : items.length - 1
          itemRefs.current[next]?.focus()
          return next
        })
        break
      
      case 'Enter':
      case ' ':
        event.preventDefault()
        if (focusedIndex >= 0 && focusedIndex < items.length) {
          const item = items[focusedIndex]
          if (!item.disabled) {
            onItemToggle(item.id, !item.visible)
          }
        }
        break
      
      case 'Home':
        event.preventDefault()
        setFocusedIndex(0)
        itemRefs.current[0]?.focus()
        break
      
      case 'End':
        event.preventDefault()
        const lastIndex = items.length - 1
        setFocusedIndex(lastIndex)
        itemRefs.current[lastIndex]?.focus()
        break
    }
  }, [interactive, items, focusedIndex, onItemToggle])

  // Handle item toggle
  const handleItemToggle = useCallback((item) => {
    if (!interactive || item.disabled) return
    onItemToggle(item.id, !item.visible)
  }, [interactive, onItemToggle])

  // Handle toggle all
  const handleToggleAll = useCallback(() => {
    const allVisible = items.every(item => item.visible || item.disabled)
    items.forEach(item => {
      if (!item.disabled) {
        onItemToggle(item.id, !allVisible)
      }
    })
  }, [items, onItemToggle])

  // Get symbol component
  const getSymbol = useCallback((item, index) => {
    const symbolColor = item.visible ? item.color : chartTokens.colors.neutral.gray400
    const symbolClass = cn(
      config.symbol,
      'flex-shrink-0',
      item.disabled && 'opacity-50',
      symbolType === 'circle' && 'rounded-full',
      symbolType === 'square' && 'rounded-sm'
    )

    if (symbolType === 'line') {
      return (
        <div 
          className={cn(config.symbol, 'flex items-center')}
          aria-hidden="true"
        >
          <div 
            className="w-full h-0.5 rounded"
            style={{ backgroundColor: symbolColor }}
          />
        </div>
      )
    }

    return (
      <div
        className={symbolClass}
        style={{ backgroundColor: symbolColor }}
        aria-hidden="true"
      />
    )
  }, [config.symbol, symbolType])

  // Layout classes
  const layoutClasses = {
    horizontal: 'flex flex-wrap items-center',
    vertical: 'flex flex-col items-start'
  }

  const positionClasses = {
    top: 'mb-4',
    bottom: 'mt-4',
    left: 'mr-4',
    right: 'ml-4'
  }

  // Stats for accessibility
  const visibleCount = items.filter(item => item.visible).length
  const totalCount = items.filter(item => !item.disabled).length

  return (
    <div 
      ref={legendRef}
      className={cn(
        'chart-legend',
        layoutClasses[layout],
        positionClasses[position],
        config.gap,
        className
      )}
      role="group"
      aria-label={`Chart legend with ${totalCount} series, ${visibleCount} visible`}
      onKeyDown={handleKeyDown}
    >
      {/* Toggle All Button */}
      {showToggleAll && interactive && items.length > 1 && (
        <button
          onClick={handleToggleAll}
          className={cn(
            'flex items-center space-x-1',
            config.text,
            config.padding,
            'text-gray-600 dark:text-gray-400',
            'hover:text-gray-800 dark:hover:text-gray-200',
            'border border-gray-300 dark:border-gray-600',
            'rounded-md transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-primary-500'
          )}
          aria-label={`Toggle all series ${visibleCount === totalCount ? 'off' : 'on'}`}
        >
          {visibleCount === totalCount ? (
            <EyeOff className="w-3 h-3" />
          ) : (
            <Eye className="w-3 h-3" />
          )}
          <span>
            {visibleCount === totalCount ? 'Hide All' : 'Show All'}
          </span>
        </button>
      )}

      {/* Legend Items */}
      {items.map((item, index) => (
        <div
          key={item.id}
          ref={el => itemRefs.current[index] = el}
          tabIndex={interactive ? 0 : -1}
          role={interactive ? 'button' : 'listitem'}
          className={cn(
            'flex items-center space-x-2 cursor-pointer select-none',
            config.padding,
            'rounded transition-all duration-200',
            interactive && !item.disabled && [
              'hover:bg-gray-100 dark:hover:bg-gray-800',
              'focus:outline-none focus:ring-2 focus:ring-primary-500'
            ],
            !item.visible && 'opacity-60',
            item.disabled && 'opacity-40 cursor-not-allowed',
            focusedIndex === index && 'ring-2 ring-primary-500'
          )}
          onClick={() => handleItemToggle(item)}
          onFocus={() => setFocusedIndex(index)}
          onBlur={() => setFocusedIndex(-1)}
          aria-pressed={interactive ? item.visible : undefined}
          aria-disabled={item.disabled}
          aria-label={`${item.label} series, ${item.visible ? 'visible' : 'hidden'}${item.disabled ? ', disabled' : ''}`}
        >
          {/* Color Symbol */}
          {showSymbols && getSymbol(item, index)}

          {/* Label */}
          <span 
            className={cn(
              config.text,
              'text-gray-700 dark:text-gray-300',
              !item.visible && 'line-through',
              item.disabled && 'text-gray-400 dark:text-gray-500'
            )}
          >
            {item.label}
          </span>

          {/* Visibility Icon (for screen readers and small screens) */}
          {interactive && !item.disabled && (
            <span className="sr-only md:not-sr-only">
              {item.visible ? (
                <Eye className="w-3 h-3 text-gray-400" />
              ) : (
                <EyeOff className="w-3 h-3 text-gray-400" />
              )}
            </span>
          )}
        </div>
      ))}

      {/* Empty State */}
      {items.length === 0 && (
        <div className={cn(
          'text-gray-500 dark:text-gray-400 italic',
          config.text,
          config.padding
        )}>
          No legend items
        </div>
      )}

      {/* Screen Reader Instructions */}
      <div className="sr-only" aria-live="polite">
        {interactive && items.length > 0 && (
          <div>
            Use arrow keys to navigate legend items. 
            Press Enter or Space to toggle series visibility.
            Press Home or End to jump to first or last item.
            {showToggleAll && ' Press Tab to access toggle all button.'}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Legend item generator helper
 * @param {Array} data - Chart data or series config
 * @param {Object} options - Generation options
 * @returns {Array} Legend items array
 */
export function generateLegendItems(data, options = {}) {
  const {
    colorPalette = chartTokens.colors.chart.categorical.primary,
    getLabel = (item, index) => item.name || item.label || `Series ${index + 1}`,
    getColor = (item, index) => colorPalette[index % colorPalette.length],
    isVisible = () => true,
    isDisabled = () => false
  } = options

  if (!Array.isArray(data)) return []

  return data.map((item, index) => ({
    id: item.id || item.key || index,
    label: getLabel(item, index),
    color: getColor(item, index),
    visible: isVisible(item, index),
    disabled: isDisabled(item, index)
  }))
}

/**
 * Legend position utilities
 */
export const legendPositions = {
  TOP: 'top',
  BOTTOM: 'bottom',
  LEFT: 'left',
  RIGHT: 'right'
}

export const legendLayouts = {
  HORIZONTAL: 'horizontal',
  VERTICAL: 'vertical'
}

export const legendSizes = {
  SMALL: 'sm',
  MEDIUM: 'md',
  LARGE: 'lg'
}

export const legendSymbolTypes = {
  SQUARE: 'square',
  CIRCLE: 'circle',
  LINE: 'line'
}