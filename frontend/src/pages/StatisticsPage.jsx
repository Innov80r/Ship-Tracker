import React, { useEffect, useMemo, useState } from 'react'
import useIntelStore from '../store/intelStore'
import useVesselStore from '../store/vesselStore'
import { PageHeader, Panel, Pill, StatTile } from '../components/ui/CommandPrimitives'
import { getApi } from '../utils/api'
import { getVesselCategory, isDarkVessel } from '../utils/intel'

export default function StatisticsPage() {
  const vesselsMap = useVesselStore((state) => state.vessels)
  const vessels = React.useMemo(() => Object.values(vesselsMap), [vesselsMap])
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const [analytics, setAnalytics] = useState({
    military: [],
    weatherImpact: [],
    corridors: [],
    correlations: [],
  })

  useEffect(() => {
    let cancelled = false

    const loadAnalytics = async () => {
      const [militaryResult, weatherResult, corridorResult, correlationResult] = await Promise.allSettled([
        getApi('/api/intel/military', { params: { limit: 10 } }),
        getApi('/api/intel/weather-impact', { params: { limit: 10 } }),
        getApi('/api/intel/corridors', { params: { limit: 10 } }),
        getApi('/api/intel/external-events/correlations', { params: { radius_nm: 120, hours: 168 } }),
      ])

      if (cancelled) return

      setAnalytics({
        military: militaryResult.status === 'fulfilled' ? militaryResult.value.vessels || [] : [],
        weatherImpact: weatherResult.status === 'fulfilled' ? weatherResult.value.vessels || [] : [],
        corridors: corridorResult.status === 'fulfilled' ? corridorResult.value.corridors || [] : [],
        correlations: correlationResult.status === 'fulfilled' ? correlationResult.value.correlations || [] : [],
      })
    }

    loadAnalytics()
    const intervalId = window.setInterval(loadAnalytics, 45000)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  const customFleet = useMemo(() => vessels.filter((vessel) => watchlistMmsis.includes(vessel.mmsi)), [vessels, watchlistMmsis])

  const overview = useMemo(() => ({
    military: analytics.military.length,
    weatherImpact: analytics.weatherImpact.length,
    correlations: analytics.correlations.length,
    customFleet: customFleet.length,
  }), [analytics.correlations.length, analytics.military.length, analytics.weatherImpact.length, customFleet.length])

  return (
    <div className="page-scroll" id="statistics-page">
      <PageHeader
        eyebrow="Fleet atlas"
        title="Fleet Segmentation & Analytics"
        subtitle="Use this page as the backend-driven analytics surface for military traffic, weather pressure, corridor density, external-event proximity, and your local custom fleet."
        actions={(
          <>
            <Pill tone="cyan">{overview.customFleet} custom fleet</Pill>
            <Pill tone="emerald">{overview.weatherImpact} weather pressure</Pill>
            <Pill tone="rose">{overview.military} military/security</Pill>
          </>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Custom fleet" value={overview.customFleet} caption="Pinned watchlist vessels" tone="cyan" />
        <StatTile label="Military" value={overview.military} caption="Backend military/security board size" tone="rose" />
        <StatTile label="Weather pressure" value={overview.weatherImpact} caption="Top vessels affected by weather" tone="emerald" />
        <StatTile label="Correlations" value={overview.correlations} caption="Vessel proximity to external events" tone="amber" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Panel title="Military board" subtitle="Current military and security contacts from the backend classifier">
          {analytics.military.length === 0 ? (
            <div className="text-sm text-slate-500">No military contacts ranked yet.</div>
          ) : (
            <div className="space-y-2">
              {analytics.military.map((vessel) => (
                <div key={vessel.mmsi} className="intel-row">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{vessel.name || `MMSI ${vessel.mmsi}`}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">{vessel.flag_country || 'Unknown flag'} · {vessel.destination || 'No destination'}</div>
                  </div>
                  <Pill tone={vessel.risk?.level === 'critical' ? 'rose' : 'amber'}>{vessel.risk?.score ?? '—'}</Pill>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Weather impact" subtitle="Backend weather grid correlation for exposed vessels">
          {analytics.weatherImpact.length === 0 ? (
            <div className="text-sm text-slate-500">Weather-impact analytics appear after the backend weather grid is cached.</div>
          ) : (
            <div className="space-y-2">
              {analytics.weatherImpact.map((vessel) => (
                <div key={vessel.mmsi} className="intel-row">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{vessel.name || `MMSI ${vessel.mmsi}`}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">wind {Math.round(vessel.weather?.wind_speed || 0)} kn · wave {(vessel.weather?.wave_height || 0).toFixed(1)} m</div>
                  </div>
                  <Pill tone={vessel.weather_impact_score >= 70 ? 'rose' : 'amber'}>{vessel.weather_impact_score}</Pill>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Panel title="Traffic corridors" subtitle="Backend-derived sector density from current active traffic">
          {analytics.corridors.length === 0 ? (
            <div className="text-sm text-slate-500">No corridor analytics are available yet.</div>
          ) : (
            <div className="space-y-3">
              {analytics.corridors.map((sector, index) => (
                <div key={`${sector.latitude}-${sector.longitude}-${index}`} className="rounded-2xl border border-slate-800/90 bg-slate-950/35 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium text-white">{Number(sector.latitude).toFixed(1)}°, {Number(sector.longitude).toFixed(1)}°</div>
                    <Pill tone="cyan">{sector.vessel_count}</Pill>
                  </div>
                  <div className="mt-3 h-2 rounded-full bg-slate-900">
                    <div className="h-2 rounded-full bg-[linear-gradient(90deg,rgba(34,211,238,0.95),rgba(16,185,129,0.4))]" style={{ width: `${Math.max(12, (sector.vessel_count / Math.max(analytics.corridors[0]?.vessel_count || 1, 1)) * 100)}%` }} />
                  </div>
                  <div className="mt-2 text-xs text-slate-500">{formatCorridorCategories(sector.categories)}</div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="External correlations" subtitle="Vessels operating near stored external intelligence events">
          {analytics.correlations.length === 0 ? (
            <div className="text-sm text-slate-500">No vessel-to-event correlations were found in the selected lookback window.</div>
          ) : (
            <div className="space-y-2">
              {analytics.correlations.slice(0, 10).map((entry) => (
                <div key={`${entry.event_id}-${entry.mmsi}`} className="intel-row">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{entry.vessel_name || `MMSI ${entry.mmsi}`}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">{entry.event_type} · {entry.event_title}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Pill tone="amber">{entry.distance_nm} nm</Pill>
                    <Pill tone={entry.risk?.level === 'critical' ? 'rose' : 'slate'}>{entry.risk?.score ?? '—'}</Pill>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Panel title="Custom fleet" subtitle="Pinned vessels still behave like a local analyst roster">
          {customFleet.length === 0 ? (
            <div className="text-sm text-slate-500">Pin vessels from search or the map panel to create a custom fleet view here.</div>
          ) : (
            <div className="space-y-2">
              {customFleet.slice(0, 10).map((vessel) => (
                <div key={vessel.mmsi} className="intel-row">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{vessel.name || `MMSI ${vessel.mmsi}`}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">{getVesselCategory(vessel)} · {vessel.flag_country || 'Unknown flag'} · {vessel.destination || 'No destination'}</div>
                  </div>
                  <Pill tone={isDarkVessel(vessel) ? 'amber' : 'emerald'}>{isDarkVessel(vessel) ? 'Dark' : 'Live'}</Pill>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Atlas notes" subtitle="What this page is now intended to cover">
          <div className="space-y-3 text-sm leading-6 text-slate-400">
            <p>Use the military board to monitor naval or security contacts surfaced by the backend classifier.</p>
            <p>Use weather impact and corridor density together to identify stressed or strategically important traffic clusters.</p>
            <p>Use external correlations to spot vessels operating close to stored piracy, sanctions, or notice events without adding any user-account system.</p>
          </div>
        </Panel>
      </div>
    </div>
  )
}

function formatCorridorCategories(categories = {}) {
  const [topCategory] = Object.entries(categories).sort((left, right) => right[1] - left[1])
  return topCategory ? `${topCategory[0]} concentration` : 'Mixed traffic'
}
