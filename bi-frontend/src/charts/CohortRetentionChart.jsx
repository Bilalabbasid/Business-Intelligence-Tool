import React, { useMemo } from 'react'
import HeatmapWrapper from './HeatmapWrapper'

// Simple, dependency-free cohort retention heatmap component.
// Expects `cohortData` as an array of cohorts where each cohort is
// { name: string, retention: [0.0..1.0, ...] }
// If no data is provided, the component generates demo data.

const defaultDemoData = () => {
  const cohorts = []
  for (let i = 0; i < 8; i++) {
    const retention = []
    let base = Math.max(0.25, 1 - i * 0.08)
    for (let j = 0; j < 8 - i; j++) {
      retention.push(Math.max(0, base - j * 0.08))
    }
    cohorts.push({ name: `Cohort ${i + 1}`, retention })
  }
  return cohorts
}

function percent(n) {
  return `${Math.round(n * 100)}%`
}

function colorForValue(v) {
  // v in 0..1 -> interpolate from #f8fafc (almost white) to #1e40af (indigo)
  const start = [248, 250, 252] // #f8fafc
  const end = [30, 64, 175] // #1e40af
  const r = Math.round(start[0] + (end[0] - start[0]) * v)
  const g = Math.round(start[1] + (end[1] - start[1]) * v)
  const b = Math.round(start[2] + (end[2] - start[2]) * v)
  return `rgb(${r}, ${g}, ${b})`
}

function downloadCSV(filename, rows) {
  const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.setAttribute('download', filename)
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const CohortRetentionChart = ({ cohortData = [], height = 350 }) => {
  const data = useMemo(() => (cohortData && cohortData.length ? cohortData : defaultDemoData()), [cohortData])

  // Determine max columns
  const maxCols = useMemo(() => data.reduce((m, c) => Math.max(m, c.retention.length), 0), [data])

  return (
    <HeatmapWrapper title="Cohort Retention" height={height}>
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs text-gray-600">Heatmap shows retention % over periods</div>
        <div>
          <button
            className="btn btn-sm mr-2"
            onClick={() => {
              const maxCols = data.reduce((m, c) => Math.max(m, c.retention.length), 0)
              const header = ['Cohort', ...Array.from({ length: maxCols }).map((_, i) => `Period ${i}`)]
              const rows = [header, ...data.map(d => [d.name, ...Array.from({ length: maxCols }).map((_, i) => (d.retention[i] != null ? (d.retention[i] * 100).toFixed(2) : ''))])]
              downloadCSV('cohort_retention.csv', rows)
            }}
          >
            Export CSV
          </button>
        </div>
      </div>

      <div className="overflow-auto">
        <table className="w-full table-fixed border-collapse text-sm">
          <thead>
            <tr>
              <th className="text-left pr-4 pb-2">Cohort</th>
              {Array.from({ length: maxCols }).map((_, idx) => (
                <th key={idx} className="text-left px-2 pb-2">Period {idx}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((cohort, rowIdx) => (
              <tr key={rowIdx} className="align-top">
                <td className="pr-4 py-2 align-top font-medium">{cohort.name}</td>
                {Array.from({ length: maxCols }).map((_, colIdx) => {
                  const v = cohort.retention[colIdx]
                  const value = typeof v === 'number' ? v : null
                  const bg = value != null ? colorForValue(value) : 'transparent'
                  return (
                    <td key={colIdx} className="px-2 py-1">
                      <div
                        style={{
                          background: bg,
                          borderRadius: 6,
                          padding: '6px 8px',
                          textAlign: 'center',
                          color: value != null && value > 0.45 ? '#fff' : '#111827',
                          minWidth: 64,
                          display: 'inline-block'
                        }}
                      >
                        {value != null ? percent(value) : '—'}
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

        <div className="mt-3 text-xs text-gray-600">
          Tip: provide <code>cohortData</code> as [{'{'} name: string, retention: number[] {'}'}]
        </div>
      </HeatmapWrapper>
  )
}

export default CohortRetentionChart
