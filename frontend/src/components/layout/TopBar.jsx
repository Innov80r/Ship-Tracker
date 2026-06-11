import React from 'react'
import useVesselStore from '../../store/vesselStore'

export default function TopBar() {
  const vesselCount = useVesselStore(s => s.vesselCount)
  const vessels = useVesselStore(s => s.vessels)
  const vArr = Object.values(vessels)
  const underway = vArr.filter(v => v.nav_status === 0).length
  const anchored = vArr.filter(v => v.nav_status === 1).length
  const moored = vArr.filter(v => v.nav_status === 5).length

  const stats = [
    { label: 'Total', value: vesselCount, dotClass: '' },
    { label: 'Underway', value: underway, dotClass: 'active' },
    { label: 'Anchored', value: anchored, dotClass: 'warning' },
    { label: 'Moored', value: moored, dotClass: 'muted' },
  ]

  return (
    <div className="absolute top-3 left-3 right-20 z-[1000] grid grid-cols-2 gap-1.5 sm:flex sm:left-1/2 sm:right-auto sm:-translate-x-1/2" id="top-stats-bar">
      {stats.map(s => (
        <div key={s.label} className="stat-card min-w-0 flex items-center justify-center gap-2 px-2.5 py-1.5 text-[11px] sm:px-3 sm:text-xs">
          {s.dotClass && <span className={`indicator-dot ${s.dotClass}`} />}
          <span className="truncate text-slate-500">{s.label}</span>
          <span className="truncate font-mono font-semibold text-slate-200">{s.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}
