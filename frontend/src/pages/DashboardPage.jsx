import React, { useEffect, useMemo, useState } from 'react'
import useAlertStore from '../store/alertStore'
import useCoverageDiagnostics from '../hooks/useCoverageDiagnostics'
import useIncidentStore from '../store/incidentStore'
import useIntelStore from '../store/intelStore'
import useVesselStore from '../store/vesselStore'
import { DataRow, EmptyState, PageHeader, Panel, Pill, StatTile } from '../components/ui/CommandPrimitives'
import { formatNumber } from '../utils/formatters'
import { getApi } from '../utils/api'
import { getFleetGroups, getRiskAssessment, getVesselCategory, isDarkVessel } from '../utils/intel'

export default function DashboardPage() {
  const vesselsMap = useVesselStore((state) => state.vessels)
  const vessels = React.useMemo(() => Object.values(vesselsMap), [vesselsMap])
  const alerts = useAlertStore((state) => state.alerts)
  const unreadCount = useAlertStore((state) => state.unreadCount)
  const incidents = useIncidentStore((state) => state.incidents)
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const savedSearches = useIntelStore((state) => state.savedSearches)
  const { health, coverage } = useCoverageDiagnostics(true)
  const [boards, setBoards] = useState({
    risk: [],
    dark: [],
    weatherImpact: [],
    congestion: [],
    corridors: [],
  })

  useEffect(() => {
    let cancelled = false

    const loadBoards = async () => {
      const [riskResult, darkResult, weatherResult, congestionResult, corridorsResult] = await Promise.allSettled([
        getApi('/api/intel/risk', { params: { limit: 6 } }),
        getApi('/api/intel/dark-vessels', { params: { limit: 6, threshold_minutes: 60 } }),
        getApi('/api/intel/weather-impact', { params: { limit: 6 } }),
        getApi('/api/intel/ports/congestion', { params: { limit: 6 } }),
        getApi('/api/intel/corridors', { params: { limit: 6 } }),
      ])

      if (cancelled) return

      setBoards({
        risk: riskResult.status === 'fulfilled' ? riskResult.value.vessels || [] : [],
        dark: darkResult.status === 'fulfilled' ? darkResult.value.vessels || [] : [],
        weatherImpact: weatherResult.status === 'fulfilled' ? weatherResult.value.vessels || [] : [],
        congestion: congestionResult.status === 'fulfilled' ? congestionResult.value.ports || [] : [],
        corridors: corridorsResult.status === 'fulfilled' ? corridorsResult.value.corridors || [] : [],
      })
    }

    loadBoards()
    const intervalId = window.setInterval(loadBoards, 30000)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  const metrics = useMemo(() => {
    const riskLeaderboard = [...vessels]
      .map((vessel) => ({
        vessel,
        intel: getRiskAssessment(vessel),
      }))
      .sort((left, right) => right.intel.score - left.intel.score)

    return {
      tracked: vessels.length,
      dark: vessels.filter((vessel) => isDarkVessel(vessel)).length,
      highRisk: riskLeaderboard.filter((entry) => entry.intel.score >= 58).length,
      military: vessels.filter((vessel) => getVesselCategory(vessel) === 'military').length,
      fleetMix: getFleetGroups(vessels, 'category').slice(0, 6),
      flagMix: getFleetGroups(vessels, 'flag').slice(0, 6),
      watchlist: vessels.filter((vessel) => watchlistMmsis.includes(vessel.mmsi)).slice(0, 6),
    }
  }, [vessels, watchlistMmsis])

  return (
    <div className="page-scroll" id="dashboard-page">
      <PageHeader
        eyebrow="Mission intelligence"
        title="Operations Dashboard"
        subtitle="A live command view across fleet posture, server-side risk scoring, dark-vessel detection, chokepoints, weather pressure, and watchlisted contacts."
        actions={(
          <>
            <Pill tone="cyan">{formatNumber(metrics.tracked)} tracked</Pill>
            <Pill tone="amber">{formatNumber(unreadCount)} unread alerts</Pill>
            <Pill tone="rose">{formatNumber(incidents.filter((incident) => incident.is_active).length)} active signals</Pill>
          </>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Tracked fleet" value={formatNumber(metrics.tracked)} caption="Live contacts in current cache" tone="cyan" />
        <StatTile label="Dark vessels" value={formatNumber(metrics.dark)} caption="AIS silence or stale telemetry" tone="amber" />
        <StatTile label="High risk" value={formatNumber(metrics.highRisk)} caption="Risk score >= 58 in live cache" tone="rose" />
        <StatTile label="Military / security" value={formatNumber(metrics.military)} caption="Military and law-enforcement signatures" tone="emerald" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel title="Priority board" subtitle="Highest risk contacts from the backend intelligence engine">
          {boards.risk.length === 0 ? (
            <EmptyState title="No risk leaderboard yet" message="Backend intelligence data will appear here once vessel state is available to the API." />
          ) : (
            <div className="space-y-2">
              {boards.risk.map((entry) => (
                <DataRow
                  key={entry.mmsi}
                  title={entry.name || `MMSI ${entry.mmsi}`}
                  subtitle={`${entry.category || getVesselCategory(entry)} · ${entry.flag_country || 'Unknown flag'} · ${formatRiskFactors(entry.risk?.factors)}`}
                  value={`Risk ${entry.risk?.score ?? '—'}`}
                  tone={entry.risk?.level === 'critical' ? 'rose' : entry.risk?.level === 'high' ? 'amber' : 'slate'}
                />
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Watchlist board" subtitle="Pinned contacts for continued surveillance">
          {metrics.watchlist.length === 0 ? (
            <EmptyState title="No watchlist contacts yet" message="Pin vessels from the map or search to keep them visible in every workspace panel." />
          ) : (
            <div className="space-y-2">
              {metrics.watchlist.map((vessel) => (
                <DataRow
                  key={vessel.mmsi}
                  title={vessel.name || `MMSI ${vessel.mmsi}`}
                  subtitle={`${getVesselCategory(vessel)} · ${vessel.destination || 'No destination'} · ${vessel.data_source || 'Unknown source'}`}
                  value={isDarkVessel(vessel) ? 'Dark' : 'Live'}
                  tone={isDarkVessel(vessel) ? 'amber' : 'emerald'}
                />
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel title="Fleet mix" subtitle="Grouped by vessel category">
          <RankBars rows={metrics.fleetMix} valueKey="count" labelKey="key" />
        </Panel>

        <Panel title="Top flags" subtitle="Most represented flag states in the current picture">
          <RankBars rows={metrics.flagMix} valueKey="count" labelKey="key" />
        </Panel>

        <Panel title="Traffic corridors" subtitle="Backend-derived density sectors from the current operating picture">
          {boards.corridors.length === 0 ? (
            <EmptyState title="No corridor data yet" message="Corridor intelligence will populate once enough concurrent traffic is available." />
          ) : (
            <RankBars
              rows={boards.corridors.map((corridor) => ({
                ...corridor,
                label: formatCorridorLabel(corridor),
                count: corridor.vessel_count,
                detail: formatCorridorCategories(corridor.categories),
              }))}
              valueKey="count"
              labelKey="label"
              extraFormatter={(row) => row.detail}
            />
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Coverage diagnostics" subtitle="What the free/public AIS stack is actually seeing right now">
          <div className="grid gap-3 sm:grid-cols-2">
            <WorkflowCard
              label="Active sources"
              value={coverage.active_source_count || health.active_sources?.length || 0}
              detail={(health.active_sources || []).join(', ') || 'No active AIS source reported'}
              tone="cyan"
            />
            <WorkflowCard
              label="Flag states"
              value={coverage.unique_flag_countries || 0}
              detail={`${coverage.unknown_flag_count || 0} unresolved or unknown flags`}
              tone="emerald"
            />
            <WorkflowCard
              label="Primary source share"
              value={`${Math.round((coverage.top_source_share || 0) * 100)}%`}
              detail="Higher values usually mean uneven regional coverage"
              tone="amber"
            />
            <WorkflowCard
              label="Live fleet basis"
              value={formatNumber(coverage.active_vessels || metrics.tracked)}
              detail="Contacts currently feeding the coverage model"
              tone="rose"
            />
          </div>

          <div className="mt-4 space-y-2">
            {(coverage.warnings || []).map((warning) => (
              <div key={warning} className="rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
                {warning}
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Port congestion" subtitle="Top berth pressure and queue activity from the backend congestion model">
          {boards.congestion.length === 0 ? (
            <EmptyState title="No congestion data yet" message="Port congestion appears once ports and vessel positions are both available to the backend." />
          ) : (
            <div className="space-y-2">
              {boards.congestion.map((port) => (
                <DataRow
                  key={port.port_id}
                  title={`${port.port_name}, ${port.country || 'Unknown'}`}
                  subtitle={`${port.nearby_vessels} contacts · ${port.queued_vessels} queueing · ${port.arrivals_per_hour} arrivals/hr`}
                  value={`Score ${port.congestion_score}`}
                  tone="amber"
                />
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Panel title="Workflow posture" subtitle="Workspace readiness and current signal volume">
          <div className="space-y-3">
            <WorkflowCard label="Saved searches" value={savedSearches.length} detail="Reusable mission presets" tone="cyan" />
            <WorkflowCard label="Unread alerts" value={unreadCount} detail="Alert center backlog" tone="amber" />
            <WorkflowCard label="Active incidents" value={incidents.filter((incident) => incident.is_active).length} detail="Signals awaiting review" tone="rose" />
            <WorkflowCard label="Recent alerts" value={alerts.slice(0, 5).length} detail="Newest alert entries loaded" tone="emerald" />
          </div>
        </Panel>

        <Panel title="Dark-vessel board" subtitle="Longest AIS gaps detected by the backend">
          {boards.dark.length === 0 ? (
            <EmptyState title="No dark contacts ranked yet" message="Dark-vessel detections appear here when recent telemetry gaps exceed the backend threshold." />
          ) : (
            <div className="space-y-2">
              {boards.dark.map((entry) => (
                <DataRow
                  key={entry.mmsi}
                  title={entry.name || `MMSI ${entry.mmsi}`}
                  subtitle={`${entry.category || getVesselCategory(entry)} · ${entry.flag_country || 'Unknown flag'} · ${Math.round(entry.last_seen_minutes || 0)} min silent`}
                  value="Dark"
                  tone="amber"
                />
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Weather pressure" subtitle="Contacts currently most affected by wind and wave state">
          {boards.weatherImpact.length === 0 ? (
            <EmptyState title="No weather pressure board yet" message="Weather impact appears after the backend weather grid has been cached." />
          ) : (
            <div className="space-y-2">
              {boards.weatherImpact.map((entry) => (
                <DataRow
                  key={entry.mmsi}
                  title={entry.name || `MMSI ${entry.mmsi}`}
                  subtitle={`${entry.category || getVesselCategory(entry)} · wind ${Math.round(entry.weather?.wind_speed || 0)} kn · wave ${(entry.weather?.wave_height || 0).toFixed(1)} m`}
                  value={`WX ${entry.weather_impact_score}`}
                  tone={entry.weather_impact_score >= 70 ? 'rose' : 'amber'}
                />
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}

function RankBars({ rows, valueKey, labelKey, extraFormatter }) {
  const maxValue = Math.max(...rows.map((row) => row[valueKey] || 0), 1)

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div key={`${row[labelKey]}-${row[valueKey]}`} className="rounded-2xl border border-slate-800/90 bg-slate-950/35 p-3">
          <div className="flex items-center justify-between gap-3 text-sm">
            <div className="truncate font-medium text-white">{row[labelKey]}</div>
            <div className="font-mono text-slate-300">{row[valueKey]}</div>
          </div>
          <div className="mt-3 h-2 rounded-full bg-slate-900">
            <div className="h-2 rounded-full bg-[linear-gradient(90deg,rgba(56,189,248,0.95),rgba(34,211,238,0.4))]" style={{ width: `${Math.max(10, (row[valueKey] / maxValue) * 100)}%` }} />
          </div>
          {extraFormatter && <div className="mt-2 text-xs text-slate-500">{extraFormatter(row)}</div>}
        </div>
      ))}
    </div>
  )
}

function WorkflowCard({ label, value, detail, tone = 'cyan' }) {
  const toneClass = {
    cyan: 'border-cyan-400/20 bg-cyan-400/8',
    amber: 'border-amber-400/20 bg-amber-400/8',
    rose: 'border-rose-400/20 bg-rose-400/8',
    emerald: 'border-emerald-400/20 bg-emerald-400/8',
  }

  return (
    <div className={`rounded-2xl border p-4 ${toneClass[tone] || toneClass.cyan}`}>
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-3xl font-semibold tracking-tight text-white">{value}</div>
      <div className="mt-2 text-sm text-slate-400">{detail}</div>
    </div>
  )
}

function formatRiskFactors(factors = []) {
  if (!factors.length) return 'General monitoring'
  return factors
    .slice(0, 2)
    .map((factor) => factor.factor.replaceAll('_', ' '))
    .join(', ')
}

function formatCorridorLabel(corridor) {
  return `${Number(corridor.latitude).toFixed(1)}°, ${Number(corridor.longitude).toFixed(1)}°`
}

function formatCorridorCategories(categories = {}) {
  const [topCategory] = Object.entries(categories).sort((left, right) => right[1] - left[1])
  return topCategory ? `${topCategory[0]} concentration` : 'Mixed traffic'
}
