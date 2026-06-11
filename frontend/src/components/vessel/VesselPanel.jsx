import React, { useMemo } from 'react'
import { getNavStatus, getTypeName } from '../../utils/aisHelpers'
import { formatCoord, formatHeading, formatSpeed, formatTimeAgo } from '../../utils/formatters'
import useUIStore from '../../store/uiStore'
import useWeatherPoint from '../../hooks/useWeatherPoint'
import useIntelStore from '../../store/intelStore'
import { Panel, Pill } from '../ui/CommandPrimitives'
import { getRiskAssessment, getTransitEta, getVesselCategory, isDarkVessel } from '../../utils/intel'

function formatMetric(value, suffix = '', digits = 1) {
  if (value == null) return '—'
  return `${Number(value).toFixed(digits)}${suffix}`
}

export default function VesselPanel({ vessel }) {
  const closeVesselPanel = useUIStore((state) => state.closeVesselPanel)
  const { conditions, loading } = useWeatherPoint(vessel?.latitude, vessel?.longitude, Boolean(vessel))
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const analystNotes = useIntelStore((state) => state.analystNotes)
  const toggleWatchlistVessel = useIntelStore((state) => state.toggleWatchlistVessel)
  const setAnalystNote = useIntelStore((state) => state.setAnalystNote)

  const wind = conditions?.wind?.current || {}
  const marine = conditions?.marine?.current || {}
  const intel = useMemo(() => getRiskAssessment(vessel, {
    weatherPoint: {
      wind_speed: wind.wind_speed_10m,
      wave_height: marine.wave_height,
    },
  }), [marine.wave_height, vessel, wind.wind_speed_10m])
  const eta = getTransitEta(vessel)
  const isPinned = watchlistMmsis.includes(vessel?.mmsi)

  if (!vessel) return null

  const navStatusClass = vessel.nav_status === 0 ? 'active' : vessel.nav_status === 1 ? 'warning' : vessel.nav_status === 14 ? 'danger' : 'muted'

  return (
    <div className="absolute right-4 top-4 z-[1200] flex h-[calc(100%-2rem)] w-full max-w-[28rem] flex-col rounded-[2rem] border border-slate-700/70 bg-[rgba(6,10,22,0.96)] p-4 shadow-[0_30px_80px_rgba(2,6,23,0.72)] backdrop-blur-2xl" id="vessel-panel">
      <div className="mb-4 flex items-start justify-between gap-4 border-b border-slate-800/90 pb-4">
        <div>
          <div className="eyebrow">Selected contact</div>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">{vessel.name || 'Unknown vessel'}</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={`indicator-dot ${navStatusClass}`} />
            <span className="text-sm text-slate-300">{getNavStatus(vessel.nav_status)}</span>
            <Pill tone="cyan">{vessel.vessel_type_name || getTypeName(vessel.vessel_type)}</Pill>
            {vessel.data_source && <Pill tone="slate">{vessel.data_source}</Pill>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" className="btn-ghost" onClick={() => toggleWatchlistVessel(vessel.mmsi)}>
            {isPinned ? 'Pinned' : 'Pin'}
          </button>
          <button type="button" className="btn-ghost" onClick={closeVesselPanel}>
            Close
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        <Panel title="Risk envelope" subtitle="Derived operational risk, weather pressure, and transit projection">
          <div className="grid grid-cols-2 gap-3">
            <IntelCard label="Risk score" value={intel.score} caption={intel.level.toUpperCase()} tone={intel.level === 'critical' ? 'rose' : intel.level === 'high' ? 'amber' : 'cyan'} />
            <IntelCard label="Weather impact" value={intel.weatherImpact} caption={loading ? 'Refreshing' : 'Local marine conditions'} tone="emerald" />
            <IntelCard label="120nm ETA" value={eta ? new Date(eta.eta).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'} caption={eta ? `${eta.hours.toFixed(1)}h at current speed` : 'No transit model'} tone="cyan" />
            <IntelCard label="Telemetry" value={isDarkVessel(vessel) ? 'Gap' : 'Live'} caption={formatTimeAgo(vessel.last_updated)} tone={isDarkVessel(vessel) ? 'amber' : 'emerald'} />
          </div>
          {intel.reasons.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {intel.reasons.map((reason) => (
                <Pill key={reason} tone="slate">{reason}</Pill>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Identity" subtitle={`${getVesselCategory(vessel)} profile`}>
          <InfoGrid
            items={[
              ['MMSI', vessel.mmsi],
              ['IMO', vessel.imo || '—'],
              ['Call sign', vessel.call_sign || '—'],
              ['Flag', vessel.flag_country || '—'],
              ['Class', vessel.transponder_class || '—'],
              ['Category', getVesselCategory(vessel)],
            ]}
          />
        </Panel>

        <Panel title="Motion" subtitle="Heading, course, speed, and dimensions">
          <InfoGrid
            items={[
              ['Speed', formatSpeed(vessel.speed)],
              ['Heading', formatHeading(vessel.heading)],
              ['Course', formatHeading(vessel.course)],
              ['ROT', vessel.rot != null ? `${vessel.rot.toFixed(1)}°/min` : '—'],
              ['Length', vessel.length ? `${vessel.length} m` : '—'],
              ['Draught', vessel.draught ? `${vessel.draught} m` : '—'],
            ]}
          />
        </Panel>

        <Panel title="Voyage" subtitle="Current position, destination, and mission context">
          <InfoGrid
            items={[
              ['Coordinates', formatCoord(vessel.latitude, vessel.longitude)],
              ['Destination', vessel.destination || '—'],
              ['ETA', vessel.eta ? new Date(vessel.eta).toLocaleString() : '—'],
              ['Updated', formatTimeAgo(vessel.last_updated)],
            ]}
          />
          <div className="mt-4 flex gap-2">
            <a
              href={`https://www.google.com/maps?q=${vessel.latitude},${vessel.longitude}`}
              target="_blank"
              rel="noopener"
              className="btn-ghost"
            >
              Open map
            </a>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => navigator.clipboard.writeText(`${vessel.latitude}, ${vessel.longitude}`)}
            >
              Copy coords
            </button>
          </div>
        </Panel>

        <Panel title="Local conditions" subtitle="Near-vessel weather and sea state">
          <InfoGrid
            items={[
              ['Temperature', formatMetric(wind.temperature_2m, '°C')],
              ['Wind speed', formatMetric(wind.wind_speed_10m, ' km/h')],
              ['Wind dir', formatMetric(wind.wind_direction_10m, '°', 0)],
              ['Wave height', formatMetric(marine.wave_height, ' m')],
              ['Wave period', formatMetric(marine.wave_period, ' s')],
              ['Pressure', formatMetric(wind.surface_pressure, ' hPa')],
            ]}
          />
          <div className="mt-3 text-xs text-slate-500">
            {loading ? 'Loading local conditions…' : conditions ? 'Open-Meteo point forecast' : 'Marine conditions unavailable'}
          </div>
        </Panel>

        <Panel title="Analyst note" subtitle="Local workspace note for this contact">
          <textarea
            value={analystNotes[vessel.mmsi] || ''}
            onChange={(event) => setAnalystNote(vessel.mmsi, event.target.value)}
            placeholder="Record ownership, mission patterns, sanctions relevance, or analyst observations…"
            className="input-field min-h-28 w-full resize-y"
          />
        </Panel>
      </div>
    </div>
  )
}

function IntelCard({ label, value, caption, tone = 'cyan' }) {
  const toneClass = {
    cyan: 'border-cyan-400/20 bg-cyan-400/8 text-cyan-100',
    emerald: 'border-emerald-400/20 bg-emerald-400/8 text-emerald-100',
    amber: 'border-amber-400/20 bg-amber-400/8 text-amber-100',
    rose: 'border-rose-400/20 bg-rose-400/8 text-rose-100',
  }

  return (
    <div className={`rounded-2xl border p-3 ${toneClass[tone] || toneClass.cyan}`}>
      <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight">{value}</div>
      <div className="mt-1 text-xs text-slate-400">{caption}</div>
    </div>
  )
}

function InfoGrid({ items }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-2xl border border-slate-800/90 bg-slate-950/40 p-3">
          <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
          <div className="mt-2 text-sm font-medium text-white">{value}</div>
        </div>
      ))}
    </div>
  )
}
