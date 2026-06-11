import React, { useMemo } from 'react'
import useIncidents from '../hooks/useIncidents'
import useVesselStore from '../store/vesselStore'
import { PageHeader, Panel, Pill, StatTile } from '../components/ui/CommandPrimitives'
import { formatCoord, formatTimeAgo } from '../utils/formatters'
import { getRiskAssessment, getVesselCategory, isDarkVessel, isMilitaryVessel } from '../utils/intel'

export default function () {
  const vesselsMap = useVesselStore((state) => state.vessels);
  const { incidents, activeCount, resolve } = useIncidents(false)
  const vessels = React.useMemo(() => Object.values(vesselsMap), [vesselsMap])

  const darkContacts = useMemo(
    () => vessels.filter((vessel) => isDarkVessel(vessel)).slice(0, 8),
    [vessels],
  )

  const militaryContacts = useMemo(
    () => vessels.filter((vessel) => isMilitaryVessel(vessel)).slice(0, 8),
    [vessels],
  )

  const riskContacts = useMemo(
    () => [...vessels]
      .map((vessel) => ({ vessel, intel: getRiskAssessment(vessel) }))
      .filter((entry) => entry.intel.score >= 58)
      .sort((left, right) => right.intel.score - left.intel.score)
      .slice(0, 8),
    [vessels],
  )

  return (
    <div className="page-scroll" id="incidents-page">
      <PageHeader
        eyebrow="Signals"
        title="Incident & Anomaly Board"
        subtitle="Review confirmed incidents, dark-vessel detections, military/security traffic, and high-risk contacts in one operating view."
        actions={(
          <>
            <Pill tone="rose">{activeCount} active incidents</Pill>
            <Pill tone="amber">{darkContacts.length} dark contacts surfaced</Pill>
            <Pill tone="cyan">{militaryContacts.length} military/security</Pill>
          </>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Active incidents" value={activeCount} caption="Confirmed signals requiring review" tone="rose" />
        <StatTile label="Dark contacts" value={darkContacts.length} caption="Stale telemetry in current cache" tone="amber" />
        <StatTile label="Military / security" value={militaryContacts.length} caption="Operationally sensitive traffic" tone="cyan" />
        <StatTile label="High risk" value={riskContacts.length} caption="Risk score 58 and above" tone="emerald" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel title="Incident feed" subtitle="Live incidents from detection services">
          {incidents.length === 0 ? (
            <div className="text-sm text-slate-500">No incidents detected right now.</div>
          ) : (
            <div className="space-y-2">
              {incidents.map((incident) => (
                <div key={incident.id} className="intel-row">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{incident.vessel_name || `MMSI ${incident.mmsi}`}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">{incident.description}</div>
                    <div className="mt-2 text-[11px] text-slate-600">{incident.incident_type} · {formatCoord(incident.latitude, incident.longitude)} · {formatTimeAgo(incident.detected_at)}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Pill tone={incident.is_active ? 'rose' : 'emerald'}>{incident.is_active ? 'Active' : 'Resolved'}</Pill>
                    {incident.is_active && (
                      <button type="button" className="btn-ghost" onClick={() => resolve(incident.id)}>
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="High-risk contacts" subtitle="Derived operational risk outside confirmed incidents">
          <div className="space-y-2">
            {riskContacts.map(({ vessel, intel }) => (
              <div key={vessel.mmsi} className="intel-row">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{vessel.name || `MMSI ${vessel.mmsi}`}</div>
                  <div className="mt-1 truncate text-xs text-slate-500">{getVesselCategory(vessel)} · {vessel.destination || 'No destination'} · {intel.reasons.join(', ') || 'General monitoring'}</div>
                </div>
                <Pill tone={intel.level === 'critical' ? 'rose' : 'amber'}>{intel.score}</Pill>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Dark vessel board" subtitle="Contacts with stale telemetry or AIS silence">
          <div className="space-y-2">
            {darkContacts.map((vessel) => (
              <div key={vessel.mmsi} className="intel-row">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{vessel.name || `MMSI ${vessel.mmsi}`}</div>
                  <div className="mt-1 truncate text-xs text-slate-500">{getVesselCategory(vessel)} · {vessel.flag_country || 'Unknown flag'}</div>
                </div>
                <Pill tone="amber">Dark</Pill>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Military / security board" subtitle="Military and security signatures from the current operating picture">
          <div className="space-y-2">
            {militaryContacts.map((vessel) => (
              <div key={vessel.mmsi} className="intel-row">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{vessel.name || `MMSI ${vessel.mmsi}`}</div>
                  <div className="mt-1 truncate text-xs text-slate-500">{vessel.flag_country || 'Unknown flag'} · {vessel.destination || 'No destination'} · {vessel.data_source || 'Unknown source'}</div>
                </div>
                <Pill tone="cyan">{getVesselCategory(vessel)}</Pill>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  )
}
