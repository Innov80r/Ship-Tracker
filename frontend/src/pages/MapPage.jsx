import React, { useEffect, useMemo, useState } from 'react'
import { useShallow } from 'zustand/react/shallow'
import Map from '../components/map/Map'
import LayerControl from '../components/map/LayerControl'
import VesselPanel from '../components/vessel/VesselPanel'
import OperationsPanel from '../components/ops/OperationsPanel'
import { Pill, Panel, StatTile } from '../components/ui/CommandPrimitives'
import useFilterStore, { selectFilterSnapshot } from '../store/filterStore'
import useIntelStore from '../store/intelStore'
import useMapStore from '../store/mapStore'
import useUIStore from '../store/uiStore'
import useVesselStore from '../store/vesselStore'
import usePorts from '../hooks/usePorts'
import useCountryCatalog from '../hooks/useCountryCatalog'
import useLayerGeoJson from '../hooks/useLayerGeoJson'
import { buildCountryDirectory, filterPortsByCountry, filterVesselsByCountry, findCountryMatch, getFlaggedVesselsByCountry } from '../utils/countryMode'
import { filterVessels, getRiskAssessment, getTransitEta, getVesselCategory, isDarkVessel } from '../utils/intel'
import { formatHeading, formatSpeed } from '../utils/formatters'

export default function MapPage() {
  const vesselsMap = useVesselStore((state) => state.vessels)
  const vessels = useMemo(() => Object.values(vesselsMap), [vesselsMap])
  const selectedVessel = useVesselStore((state) => state.selectedVessel)
  const vesselPanelOpen = useUIStore((state) => state.vesselPanelOpen)
  const layerControlOpen = useUIStore((state) => state.layerControlOpen)
  const toggleLayerControl = useUIStore((state) => state.toggleLayerControl)
  const closeLayerControl = useUIStore((state) => state.closeLayerControl)
  const activeLayers = useMapStore((state) => state.activeLayers)
  const selectedCountryKey = useMapStore((state) => state.selectedCountryKey)
  const setSelectedCountryKey = useMapStore((state) => state.setSelectedCountryKey)
  const flyTo = useMapStore((state) => state.flyTo)
  const filters = useFilterStore(useShallow(selectFilterSnapshot))
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const toggleWatchlistVessel = useIntelStore((state) => state.toggleWatchlistVessel)
  const countryModeActive = Boolean(selectedCountryKey)
  const { ports } = usePorts(activeLayers.ports || countryModeActive)
  const countryCatalog = useCountryCatalog(true)
  const eezGeoJson = useLayerGeoJson('/api/layers/eez', activeLayers.eez || countryModeActive)
  const countryDirectory = useMemo(
    () => buildCountryDirectory(eezGeoJson, { catalogCountries: countryCatalog, ports }),
    [countryCatalog, eezGeoJson, ports],
  )
  const selectedCountry = useMemo(
    () => countryDirectory.find((country) => country.key === selectedCountryKey) || null,
    [countryDirectory, selectedCountryKey],
  )
  const [countryQuery, setCountryQuery] = useState('')

  useEffect(() => {
    setCountryQuery(selectedCountry?.name || '')
  }, [selectedCountry])

  const visibleVessels = useMemo(() => {
    const baseVessels = filterVessels(vessels, filters, watchlistMmsis)
    return selectedCountry ? filterVesselsByCountry(baseVessels, selectedCountry) : baseVessels
  }, [vessels, filters, watchlistMmsis, selectedCountry])

  const countryTraffic = useMemo(
    () => (selectedCountry ? filterVesselsByCountry(vessels, selectedCountry) : []),
    [selectedCountry, vessels],
  )
  const countryPorts = useMemo(
    () => (selectedCountry ? filterPortsByCountry(ports, selectedCountry) : []),
    [ports, selectedCountry],
  )
  const countryFlaggedTraffic = useMemo(
    () => (selectedCountry ? getFlaggedVesselsByCountry(vessels, selectedCountry) : []),
    [selectedCountry, vessels],
  )

  const metrics = useMemo(() => {
    const underway = visibleVessels.filter((vessel) => vessel.nav_status === 0).length
    const dark = visibleVessels.filter((vessel) => isDarkVessel(vessel)).length
    const highRisk = visibleVessels.filter((vessel) => getRiskAssessment(vessel).score >= 58).length
    const watchlist = visibleVessels.filter((vessel) => watchlistMmsis.includes(vessel.mmsi)).length

    return { underway, dark, highRisk, watchlist }
  }, [visibleVessels, watchlistMmsis])

  const selectedRisk = selectedVessel ? getRiskAssessment(selectedVessel) : null
  const selectedEta = selectedVessel ? getTransitEta(selectedVessel) : null
  const enabledLayerCount = useMemo(
    () => Object.values(activeLayers).filter(Boolean).length,
    [activeLayers],
  )

  const applyCountrySelection = () => {
    const match = findCountryMatch(countryDirectory, countryQuery)
    if (!match) return
    setSelectedCountryKey(match.key)
    flyTo(match.center[0], match.center[1], match.zoom)
  }

  const clearCountrySelection = () => {
    setSelectedCountryKey(null)
    setCountryQuery('')
  }

  return (
    <div className="relative h-full overflow-hidden rounded-[2rem]" id="map-page">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(14,165,233,0.12),transparent_30%)]" />
      <LayerControl open={layerControlOpen} onClose={closeLayerControl} />

      <div className="relative z-10 flex h-full min-h-0 flex-col gap-4 p-4 md:p-6">
        <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[23.5rem_minmax(0,1fr)_23.5rem]">
          <div className="min-h-0 space-y-3 overflow-y-auto pr-1">
            <div className="pointer-events-auto space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <StatTile label="Visible contacts" value={visibleVessels.length.toLocaleString()} caption="Current filtered operating picture" tone="cyan" />
                <StatTile label="Underway" value={metrics.underway.toLocaleString()} caption="Engines engaged in current view" tone="emerald" />
                <StatTile label="Dark / stale" value={metrics.dark.toLocaleString()} caption="Telemetry gaps needing review" tone="amber" />
                <StatTile label="High risk" value={metrics.highRisk.toLocaleString()} caption="Elevated contacts in filtered set" tone="rose" />
              </div>
              <OperationsPanel />
            </div>
          </div>

          <div className="min-h-0">
            <div className="relative h-full min-h-[28rem] overflow-hidden rounded-[2rem] border border-cyan-400/10 bg-[#020617] shadow-[inset_0_1px_0_rgba(255,255,255,0.03),0_30px_90px_rgba(2,6,23,0.5)]">
              <div className="pointer-events-auto absolute right-4 top-4 z-[1000]">
                <button
                  type="button"
                  onClick={toggleLayerControl}
                  className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-[11px] font-medium uppercase tracking-[0.18em] backdrop-blur-sm transition ${
                    layerControlOpen
                      ? 'border-cyan-400/30 bg-cyan-400/12 text-cyan-100'
                      : 'border-slate-700/80 bg-slate-950/70 text-slate-200 hover:border-slate-500/70'
                  }`}
                >
                  <span>Layers</span>
                  <span className="rounded-full border border-current/20 px-2 py-0.5 text-[10px] leading-none">
                    {enabledLayerCount}
                  </span>
                </button>
              </div>

              <Map />

              <div className="pointer-events-auto absolute bottom-4 right-4 z-[1000] hidden max-w-[calc(100%-2rem)] xl:block">
                <div className="surface-strip flex flex-wrap items-center gap-2">
                  {selectedCountry && <Pill tone="cyan">Country: {selectedCountry.name}</Pill>}
                  <Pill tone="cyan">Projected route enabled</Pill>
                  <Pill tone="slate">Watchlist: {watchlistMmsis.length}</Pill>
                  <Pill tone="amber">Telemetry threshold: {filters.lastSeenMaxMinutes}m</Pill>
                </div>
              </div>

              <div className="pointer-events-none absolute inset-0 rounded-[2rem] ring-1 ring-inset ring-white/5" />
            </div>
          </div>

          <div className="min-h-0 space-y-3 overflow-y-auto pl-1">
            <div className="pointer-events-auto space-y-3">
              <Panel
                title="Mission control"
                subtitle="Map controls and live contact snapshot"
              >
                <div className="grid grid-cols-2 gap-2">
                  <QuickChip label="Watchlist" value={metrics.watchlist} tone="cyan" />
                  <QuickChip label="Mode" value="Chart" tone="emerald" />
                  <QuickChip label="Risk floor" value={filters.riskMinimum} tone="rose" />
                  <QuickChip label="Layers live" value={enabledLayerCount} tone="slate" />
                </div>
              </Panel>

              <Panel
                title="Country mode"
                subtitle="Search a country or EEZ territory, jump the map there, and scope traffic and ports to that area"
              >
                <div className="space-y-3">
                  <label className="block">
                    <div className="eyebrow-sm">Country or territory</div>
                    <input
                      list="country-mode-options"
                      type="text"
                      value={countryQuery}
                      onChange={(event) => setCountryQuery(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          applyCountrySelection()
                        }
                      }}
                      className="input-field mt-2 w-full"
                      placeholder="India, Brazil, Japan, Norway..."
                    />
                    <datalist id="country-mode-options">
                      {countryDirectory.map((country) => (
                        <option key={country.key} value={country.name} />
                      ))}
                    </datalist>
                  </label>

                  <div className="flex flex-wrap gap-2">
                    <button type="button" className="btn-primary" onClick={applyCountrySelection} disabled={!countryQuery.trim()}>
                      Apply country
                    </button>
                    <button type="button" className="btn-ghost" onClick={clearCountrySelection} disabled={!selectedCountry}>
                      Clear
                    </button>
                    {selectedCountry && <Pill tone="cyan">{selectedCountry.name}</Pill>}
                  </div>

                  {selectedCountry ? (
                    <div className="space-y-2">
                      <div className="grid gap-2 sm:grid-cols-3">
                        <QuickChip label="Ports" value={countryPorts.length} tone="amber" />
                        <QuickChip label={selectedCountry.hasGeometry ? 'In waters' : 'Matched traffic'} value={countryTraffic.length} tone="emerald" />
                        <QuickChip label="Flagged" value={countryFlaggedTraffic.length} tone="rose" />
                      </div>
                      {!selectedCountry.hasGeometry && (
                        <div className="rounded-2xl border border-slate-800/90 bg-slate-950/35 p-3 text-sm text-slate-500">
                          This country has no EEZ polygon in the map layer, so traffic falls back to flag-country matches.
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-slate-800/90 bg-slate-950/35 p-3 text-sm text-slate-500">
                      Country mode is off. Apply a country to focus the map on that area and count local ports and vessel traffic.
                    </div>
                  )}
                </div>
              </Panel>

              {selectedVessel && (
                <Panel
                  title={selectedVessel.name || `MMSI ${selectedVessel.mmsi}`}
                  subtitle={`${getVesselCategory(selectedVessel)} contact · ${selectedVessel.flag_country || 'Unknown flag'}`}
                  action={(
                    <button type="button" className="btn-ghost" onClick={() => toggleWatchlistVessel(selectedVessel.mmsi)}>
                      {watchlistMmsis.includes(selectedVessel.mmsi) ? 'Unpin' : 'Pin'}
                    </button>
                  )}
                >
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Pill tone={selectedRisk?.level === 'critical' ? 'rose' : selectedRisk?.level === 'high' ? 'amber' : 'cyan'}>
                        Risk {selectedRisk?.score ?? 0}
                      </Pill>
                      {isDarkVessel(selectedVessel) && <Pill tone="amber">Dark vessel</Pill>}
                      {selectedVessel.destination && <Pill tone="emerald">{selectedVessel.destination}</Pill>}
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm text-slate-300">
                      <MetricLine label="Speed" value={formatSpeed(selectedVessel.speed)} />
                      <MetricLine label="Heading" value={formatHeading(selectedVessel.heading || selectedVessel.course)} />
                      <MetricLine label="Type" value={selectedVessel.vessel_type_name || 'Unknown'} />
                      <MetricLine label="Source" value={selectedVessel.data_source || 'Unknown'} />
                      <MetricLine label="120nm ETA" value={selectedEta ? new Date(selectedEta.eta).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'} />
                      <MetricLine label="Course" value={formatHeading(selectedVessel.course)} />
                    </div>
                    {selectedRisk?.reasons?.length > 0 && (
                      <div className="rounded-2xl border border-slate-800/90 bg-slate-950/45 p-3">
                        <div className="eyebrow-sm">Risk drivers</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {selectedRisk.reasons.map((reason) => (
                            <Pill key={reason} tone="slate">{reason}</Pill>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </Panel>
              )}
            </div>
          </div>
        </div>

        <div className="pointer-events-auto flex justify-end xl:hidden">
          <div className="surface-strip flex flex-wrap items-center gap-2">
            {selectedCountry && <Pill tone="cyan">Country: {selectedCountry.name}</Pill>}
            <Pill tone="cyan">Projected route enabled</Pill>
            <Pill tone="slate">Watchlist: {watchlistMmsis.length}</Pill>
            <Pill tone="amber">Telemetry threshold: {filters.lastSeenMaxMinutes}m</Pill>
          </div>
        </div>
      </div>

      {vesselPanelOpen && selectedVessel && <VesselPanel vessel={selectedVessel} />}
    </div>
  )
}

function QuickChip({ label, value, tone }) {
  const toneClass = {
    cyan: 'border-cyan-400/20 bg-cyan-400/8 text-cyan-100',
    emerald: 'border-emerald-400/20 bg-emerald-400/8 text-emerald-100',
    rose: 'border-rose-400/20 bg-rose-400/8 text-rose-100',
    slate: 'border-slate-500/20 bg-slate-500/8 text-slate-200',
  }

  return (
    <div className={`rounded-2xl border px-3 py-3 ${toneClass[tone] || toneClass.slate}`}>
      <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-lg font-semibold">{value}</div>
    </div>
  )
}

function MetricLine({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-800/90 bg-slate-950/35 p-3">
      <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-sm font-medium text-white">{value}</div>
    </div>
  )
}
