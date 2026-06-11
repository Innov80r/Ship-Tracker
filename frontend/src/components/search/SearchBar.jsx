import React, { useEffect, useRef, useState } from 'react'
import useMapStore from '../../store/mapStore'
import useUIStore from '../../store/uiStore'
import useVesselStore from '../../store/vesselStore'
import useIntelStore from '../../store/intelStore'
import { getTypeName } from '../../utils/aisHelpers'
import { matchesVesselSearch } from '../../utils/vesselSearch'

export default function SearchBar() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const vessels = useVesselStore((state) => state.vessels)
  const selectVessel = useVesselStore((state) => state.selectVessel)
  const flyTo = useMapStore((state) => state.flyTo)
  const openVesselPanel = useUIStore((state) => state.openVesselPanel)
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const toggleWatchlistVessel = useIntelStore((state) => state.toggleWatchlistVessel)
  const ref = useRef()

  useEffect(() => {
    const handle = (event) => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  const handleSearch = (value) => {
    setQuery(value)
    if (value.length < 2) {
      setResults([])
      setOpen(false)
      return
    }

    const matches = Object.values(vessels)
      .filter((vessel) => matchesVesselSearch(vessel, value))
      .slice(0, 12)

    setResults(matches)
    setOpen(true)
  }

  const handleSelect = (vessel) => {
    selectVessel(vessel.mmsi)
    if (vessel.latitude != null && vessel.longitude != null) {
      flyTo(vessel.latitude, vessel.longitude, 14)
    }
    openVesselPanel()
    setOpen(false)
    setQuery('')
  }

  return (
    <div className="relative w-full max-w-xl" ref={ref} id="search-bar">
      <div className="relative">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
          <circle cx="11" cy="11" r="7.5" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(event) => handleSearch(event.target.value)}
          placeholder="Locate vessel, fleet, flag, MMSI, IMO, type…"
          className="w-full rounded-full border border-slate-700/80 bg-slate-950/75 py-3 pl-12 pr-4 text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition placeholder:text-slate-600 focus:border-cyan-400/40 focus:outline-none"
        />
      </div>

      {open && results.length > 0 && (
        <div className="panel-surface absolute left-0 right-0 top-[calc(100%+0.75rem)] z-50 max-h-96 overflow-y-auto">
          <div className="mb-3 flex items-center justify-between">
            <div className="eyebrow-sm">Live search</div>
            <div className="text-xs text-slate-500">{results.length} matches</div>
          </div>
          <div className="space-y-2">
            {results.map((vessel) => {
              const pinned = watchlistMmsis.includes(vessel.mmsi)
              return (
                <div
                  key={vessel.mmsi}
                  role="button"
                  tabIndex={0}
                  onClick={() => handleSelect(vessel)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      handleSelect(vessel)
                    }
                  }}
                  className="intel-row cursor-pointer hover:border-cyan-400/20 hover:bg-cyan-400/5"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{vessel.name || `MMSI ${vessel.mmsi}`}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">
                      {getTypeName(vessel.vessel_type)} · {vessel.mmsi} · {vessel.flag_country || 'Unknown flag'}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      toggleWatchlistVessel(vessel.mmsi)
                    }}
                    className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.18em] transition ${
                      pinned
                        ? 'border-cyan-400/25 bg-cyan-400/10 text-cyan-100'
                        : 'border-slate-700/80 bg-slate-950/40 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {pinned ? 'Pinned' : 'Pin'}
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
