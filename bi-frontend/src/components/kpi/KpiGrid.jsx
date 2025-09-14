import { cn } from '../../utils'

export default function KpiGrid({ 
  children, 
  className = '',
  columns = { sm: 1, md: 2, lg: 3, xl: 4 } 
}) {
  const getGridCols = () => {
    const { sm = 1, md = 2, lg = 3, xl = 4 } = columns
    return cn(
      `grid gap-4 sm:gap-6`,
      `grid-cols-${sm}`,
      `md:grid-cols-${md}`,
      `lg:grid-cols-${lg}`,
      `xl:grid-cols-${xl}`
    )
  }

  return (
    <div className={cn(getGridCols(), className)}>
      {children}
    </div>
  )
}