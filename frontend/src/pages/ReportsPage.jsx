import React, { useEffect, useMemo, useState } from 'react'
import useAlertStore from '../store/alertStore'
import useIncidentStore from '../store/incidentStore'
import useIntelStore from '../store/intelStore'
import useVesselStore from '../store/vesselStore'
import { PageHeader, Panel, Pill, StatTile } from '../components/ui/CommandPrimitives'
import { exportAsJSON, exportAsText, exportRowsAsCSV } from '../utils/exportHelpers'
import { formatTimestamp } from '../utils/formatters'
import { getApi } from '../utils/api'

export default function ReportsPage() {
  const vesselsMap = useVesselStore((state) => state.vessels)
  const vessels = React.useMemo(() => Object.values(vesselsMap), [vesselsMap])
  const alerts = useAlertStore((state) => state.alerts)
  const incidents = useIncidentStore((state) => state.incidents)
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const workspaceName = useIntelStore((state) => state.workspaceName)
  const [report, setReport] = useState({
    generated_at: null,
    risk_leaderboard: [],
    dark_vessels: [],
    port_congestion: [],
    traffic_corridors: [],
    external_events: [],
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false

    const loadReport = async () => {
      setLoading(true)
      try {
        const data = await getApi('/api/intel/reports/briefing')
        if (!cancelled && !data.error) {
          setReport({
            generated_at: data.generated_at || null,
            risk_leaderboard: data.risk_leaderboard || [],
            dark_vessels: data.dark_vessels || [],
            port_congestion: data.port_congestion || [],
            traffic_corridors: data.traffic_corridors || [],
            external_events: data.external_events || [],
          })
        }
      } catch {
        if (!cancelled) {
          setReport({
            generated_at: null,
            risk_leaderboard: [],
            dark_vessels: [],
            port_congestion: [],
            traffic_corridors: [],
            external_events: [],
          })
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadReport()
    const intervalId = window.setInterval(loadReport, 45000)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  const summary = useMemo(() => ({
    fleetCount: vessels.length,
    watchlistCount: watchlistMmsis.length,
    darkVessels: report.dark_vessels.length,
    militaryVessels: report.risk_leaderboard.filter((entry) => entry.category === 'military').length,
  }), [report.dark_vessels.length, report.risk_leaderboard, vessels.length, watchlistMmsis.length])

  const exportBriefing = () => {
    const content = [
      `Workspace: ${workspaceName}`,
      `Generated: ${report.generated_at ? new Date(report.generated_at).toLocaleString() : 'Unavailable'}`,
      '',
      `Fleet count: ${summary.fleetCount}`,
      `Dark vessels: ${summary.darkVessels}`,
      `Military vessels: ${summary.militaryVessels}`,
      `Watchlist count: ${summary.watchlistCount}`,
      `Unread alerts loaded: ${alerts.filter((alert) => !alert.is_read).length}`,
      `Active incidents loaded: ${incidents.filter((incident) => incident.is_active).length}`,
      '',
      'Top risk contacts:',
      ...report.risk_leaderboard.map((entry) => `- ${entry.name || `MMSI ${entry.mmsi}`} (${entry.category}) risk ${entry.risk?.score ?? '—'}`),
      '',
      'External events:',
      ...report.external_events.map((event) => `- ${event.title} [${event.event_type}] ${event.region || event.country || ''}`),
    ].join('\n')

    exportAsText(content, `briefing_${Date.now()}.txt`)
  }

  const exportRiskCsv = () => {
    exportRowsAsCSV(
      ['mmsi', 'name', 'category', 'flag_country', 'risk_score', 'risk_level', 'destination'],
      report.risk_leaderboard.map((entry) => ({
        mmsi: entry.mmsi,
        name: entry.name || '',
        category: entry.category || '',
        flag_country: entry.flag_country || '',
        risk_score: entry.risk?.score ?? '',
        risk_level: entry.risk?.level ?? '',
        destination: entry.destination || '',
      })),
      `risk_leaderboard_${Date.now()}.csv`,
    )
  }

  return (
    <div className="page-scroll" id="reports-page">
      <PageHeader
        eyebrow="Reports"
        title="Operator Reporting"
        subtitle="Generate a backend intelligence briefing that includes risk leaders, dark vessels, chokepoints, traffic corridors, and external maritime events."
        actions={(
          <>
            <button type="button" className="btn-ghost" onClick={exportBriefing}>Export briefing</button>
            <button type="button" className="btn-ghost" onClick={exportRiskCsv}>Export risk CSV</button>
            <button type="button" className="btn-primary" onClick={() => exportAsJSON(report, `operator_report_${Date.now()}.json`)}>Export JSON</button>
          </>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Fleet" value={summary.fleetCount} caption="Total contacts in live report scope" tone="cyan" />
        <StatTile label="Watchlist" value={summary.watchlistCount} caption="Pinned contacts in workspace scope" tone="emerald" />
        <StatTile label="Dark" value={summary.darkVessels} caption="Dark-vessel leaderboard entries" tone="amber" />
        <StatTile label="Military" value={summary.militaryVessels} caption="Military/security profile count in briefing" tone="rose" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="Briefing summary" subtitle="Snapshot of what the report exports currently contain">
          <div className="space-y-3 text-sm leading-6 text-slate-400">
            <p>The report is generated from backend intelligence endpoints rather than local-only heuristics, so it matches the same scoring and congestion logic used by the API.</p>
            <p>Use JSON for downstream systems, CSV for spreadsheet workflows, and the text briefing for analyst handoff.</p>
            <div className="flex flex-wrap gap-2">
              <Pill tone="cyan">{report.traffic_corridors.length} corridors</Pill>
              <Pill tone="amber">{report.port_congestion.length} congestion hotspots</Pill>
              <Pill tone="rose">{report.risk_leaderboard.length} priority contacts</Pill>
              <Pill tone="slate">{loading ? 'Refreshing…' : formatTimestamp(report.generated_at)}</Pill>
            </div>
          </div>
        </Panel>

        <Panel title="Top risk contacts" subtitle="Primary contacts included in the backend briefing output">
          <div className="space-y-2">
            {report.risk_leaderboard.map((entry) => (
              <div key={entry.mmsi} className="intel-row">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{entry.name || `MMSI ${entry.mmsi}`}</div>
                  <div className="mt-1 truncate text-xs text-slate-500">{entry.category} · {entry.flag_country || 'Unknown flag'} · {entry.destination || 'No destination'}</div>
                </div>
                <div className="flex items-center gap-2">
                  {watchlistMmsis.includes(entry.mmsi) && <Pill tone="cyan">Watchlist</Pill>}
                  <Pill tone={entry.risk?.level === 'critical' ? 'rose' : entry.risk?.level === 'high' ? 'amber' : 'slate'}>
                    {entry.risk?.score ?? '—'}
                  </Pill>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Panel title="Congestion hotspots" subtitle="Ports surfaced in the backend operator briefing">
          <div className="space-y-2">
            {report.port_congestion.map((port) => (
              <div key={port.port_id} className="intel-row">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{port.port_name}</div>
                  <div className="mt-1 truncate text-xs text-slate-500">{port.country || 'Unknown'} · {port.nearby_vessels} contacts · {port.queued_vessels} queueing</div>
                </div>
                <Pill tone="amber">{port.congestion_score}</Pill>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Traffic corridors" subtitle="Backend-derived density sectors included in the briefing">
          <div className="space-y-2">
            {report.traffic_corridors.map((corridor, index) => (
              <div key={`${corridor.latitude}-${corridor.longitude}-${index}`} className="intel-row">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{Number(corridor.latitude).toFixed(1)}°, {Number(corridor.longitude).toFixed(1)}°</div>
                  <div className="mt-1 truncate text-xs text-slate-500">{formatCorridorCategories(corridor.categories)}</div>
                </div>
                <Pill tone="cyan">{corridor.vessel_count}</Pill>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel title="External events" subtitle="Stored piracy, sanctions, notice, and other external intelligence records">
        {report.external_events.length === 0 ? (
          <div className="text-sm text-slate-500">No external events are stored yet. Seed or ingest feeds to include them in the briefing.</div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {report.external_events.map((event) => (
              <div key={event.id} className="rounded-2xl border border-slate-800/90 bg-slate-950/35 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-white">{event.title}</div>
                    <div className="mt-1 text-xs text-slate-500">{event.event_type} · {event.region || event.country || 'Unknown region'}</div>
                  </div>
                  <Pill tone={event.severity === 'critical' ? 'rose' : event.severity === 'warning' ? 'amber' : 'cyan'}>
                    {event.severity}
                  </Pill>
                </div>
                <div className="mt-3 text-sm leading-6 text-slate-400">{event.summary || 'No summary provided.'}</div>
                <div className="mt-3 text-[11px] text-slate-600">{formatTimestamp(event.occurred_at)}</div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  )
}

function formatCorridorCategories(categories = {}) {
  const [topCategory] = Object.entries(categories).sort((left, right) => right[1] - left[1])
  return topCategory ? `${topCategory[0]} concentration` : 'Mixed traffic'
}
