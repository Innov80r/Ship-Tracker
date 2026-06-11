import React, { useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'
import useFilterStore, { defaultFilters, selectFilterSnapshot } from '../../store/filterStore'
import useIntelStore from '../../store/intelStore'
import useMapStore from '../../store/mapStore'
import useUIStore from '../../store/uiStore'
import useVesselStore from '../../store/vesselStore'
import { DataRow, Panel, Pill } from '../ui/CommandPrimitives'
import { filterVessels, formatLastSeen, getRiskAssessment, getVesselCategory, isDarkVessel } from '../../utils/intel'

const CATEGORY_OPTIONS = [
  { id: 'cargo', label: 'Cargo' },
  { id: 'tanker', label: 'Tanker' },
  { id: 'military', label: 'Military' },
  { id: 'security', label: 'Security' },
  { id: 'fishing', label: 'Fishing' },
  { id: 'passenger', label: 'Passenger' },
]

const LAYER_TOGGLES = [
  { key: 'openSeaMap', label: 'Charts' },
  { key: 'heatmap', label: 'Heatmap' },
  { key: 'trails', label: 'Trails' },
  { key: 'weather', label: 'Wind' },
  { key: 'waves', label: 'Waves' },
  { key: 'currents', label: 'Currents' },
  { key: 'tides', label: 'Tides' },
  { key: 'ports', label: 'Ports' },
  { key: 'incidents', label: 'Incidents' },
  { key: 'zones', label: 'Zones' },
  { key: 'cables', label: 'Cables' },
  { key: 'eez', label: 'EEZ' },
]

function toggleValue(current, value) {
  return current.includes(value)
    ? current.filter((entry) => entry !== value)
    : [...current, value]
}

export default function OperationsPanel() {
  const vesselsMap = useVesselStore((state) => state.vessels)
  const vessels = useMemo(() => Object.values(vesselsMap), [vesselsMap])
  const selectedVessel = useVesselStore((state) => state.selectedVessel)
  const selectVessel = useVesselStore((state) => state.selectVessel)
  const activeLayers = useMapStore((state) => state.activeLayers)
  const toggleLayer = useMapStore((state) => state.toggleLayer)
  const flyTo = useMapStore((state) => state.flyTo)
  const openVesselPanel = useUIStore((state) => state.openVesselPanel)

  const filters = useFilterStore(useShallow(selectFilterSnapshot))
  const patchFilters = useFilterStore((state) => state.patchFilters)
  const clearFilters = useFilterStore((state) => state.clearFilters)

  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const toggleWatchlistVessel = useIntelStore((state) => state.toggleWatchlistVessel)
  const savedSearches = useIntelStore((state) => state.savedSearches)
  const saveSearch = useIntelStore((state) => state.saveSearch)
  const deleteSavedSearch = useIntelStore((state) => state.deleteSavedSearch)

  const visibleVessels = useMemo(
    () => filterVessels(vessels, filters, watchlistMmsis),
    [vessels, filters, watchlistMmsis],
  )

  const watchlistVessels = useMemo(() => {
    const watchlistSet = new Set(watchlistMmsis)
    return vessels.filter((vessel) => watchlistSet.has(vessel.mmsi))
  }, [vessels, watchlistMmsis])

  const priorityFeed = useMemo(() => (
    [...visibleVessels]
      .map((vessel) => ({
        ...vessel,
        intel: getRiskAssessment(vessel),
      }))
      .sort((left, right) => right.intel.score - left.intel.score)
      .slice(0, 6)
  ), [visibleVessels])

  const darkCount = useMemo(
    () => visibleVessels.filter((vessel) => isDarkVessel(vessel)).length,
    [visibleVessels],
  )

  const handleSaveSearch = () => {
    const name = window.prompt('Save current search as')
    if (!name) return
    saveSearch(name, { ...filters })
  }

  const focusVessel = (vessel) => {
    selectVessel(vessel.mmsi)
    if (vessel.latitude != null && vessel.longitude != null) {
      flyTo(vessel.latitude, vessel.longitude, 8)
    }
    openVesselPanel()
  }

  return (
    <div className="pointer-events-auto flex max-h-[calc(100vh-13rem)] w-full max-w-[24rem] flex-col gap-3 overflow-hidden lg:max-w-[25rem]">
      <Panel
        title="Operations Matrix"
        subtitle={`${visibleVessels.length.toLocaleString()} visible / ${vessels.length.toLocaleString()} tracked`}
        action={(
          <button type="button" className="btn-ghost" onClick={handleSaveSearch}>
            Save search
          </button>
        )}
      >
        <div className="space-y-4">
          <div>
            <label className="eyebrow-sm">Filter query</label>
            <input
              type="text"
              value={filters.searchQuery}
              onChange={(event) => patchFilters({ searchQuery: event.target.value })}
              placeholder="military, tanker, Hormuz, IMO…"
              className="input-field mt-2 w-full"
            />
          </div>

          <div>
            <div className="eyebrow-sm">Focus classes</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {CATEGORY_OPTIONS.map((option) => {
                const active = filters.vesselCategories.includes(option.id)
                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => patchFilters({ vesselCategories: toggleValue(filters.vesselCategories, option.id) })}
                    className={`rounded-full border px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] transition ${
                      active
                        ? 'border-cyan-400/30 bg-cyan-400/12 text-cyan-100'
                        : 'border-slate-700/80 bg-slate-900/60 text-slate-400 hover:border-slate-500/60 hover:text-slate-200'
                    }`}
                  >
                    {option.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <RangeField
              label="Risk floor"
              min={0}
              max={100}
              step={5}
              value={filters.riskMinimum}
              formatter={(value) => `${value}`}
              onChange={(value) => patchFilters({ riskMinimum: value })}
            />
            <RangeField
              label="Last seen"
              min={15}
              max={720}
              step={15}
              value={filters.lastSeenMaxMinutes}
              formatter={(value) => `${value}m`}
              onChange={(value) => patchFilters({ lastSeenMaxMinutes: value })}
            />
            <RangeField
              label="Speed cap"
              min={5}
              max={45}
              step={1}
              value={filters.speedRange[1]}
              formatter={(value) => `${value} kn`}
              onChange={(value) => patchFilters({ speedRange: [filters.speedRange[0], value] })}
            />
            <RangeField
              label="Draught cap"
              min={4}
              max={20}
              step={1}
              value={filters.draughtRange[1]}
              formatter={(value) => `${value} m`}
              onChange={(value) => patchFilters({ draughtRange: [filters.draughtRange[0], value] })}
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <ToggleTag active={filters.watchlistOnly} onClick={() => patchFilters({ watchlistOnly: !filters.watchlistOnly })}>
              Watchlist only
            </ToggleTag>
            <ToggleTag active={filters.darkOnly} onClick={() => patchFilters({ darkOnly: !filters.darkOnly })}>
              Dark vessels
            </ToggleTag>
            <ToggleTag active={filters.destinationRequired} onClick={() => patchFilters({ destinationRequired: !filters.destinationRequired })}>
              Has destination
            </ToggleTag>
            <ToggleTag active={filters.weatherImpactOnly} onClick={() => patchFilters({ weatherImpactOnly: !filters.weatherImpactOnly })}>
              Weather impact
            </ToggleTag>
          </div>

          <div className="flex flex-wrap gap-2">
            <Pill tone="amber">{darkCount} dark</Pill>
            <Pill tone="rose">{priorityFeed.filter((item) => item.intel.level === 'critical').length} critical</Pill>
            <Pill tone="emerald">{watchlistVessels.length} watchlist</Pill>
            {selectedVessel && <Pill tone="cyan">{getVesselCategory(selectedVessel)}</Pill>}
          </div>

          <div className="flex gap-2">
            <button type="button" className="btn-ghost flex-1" onClick={() => clearFilters()}>
              Reset filters
            </button>
            {selectedVessel && (
              <button type="button" className="btn-primary flex-1" onClick={() => toggleWatchlistVessel(selectedVessel.mmsi)}>
                {watchlistMmsis.includes(selectedVessel.mmsi) ? 'Unpin vessel' : 'Pin vessel'}
              </button>
            )}
          </div>
        </div>
      </Panel>

      <Panel title="Saved searches" subtitle="Reusable search presets for recurring missions">
        {savedSearches.length === 0 ? (
          <div className="text-sm text-slate-500">Save your current filters to create quick launch profiles for watch sectors or vessel classes.</div>
        ) : (
          <div className="space-y-2">
            {savedSearches.slice(0, 5).map((search) => (
              <DataRow
                key={search.id}
                title={search.name}
                subtitle={describeSavedSearch(search.filters)}
                value={search.filters.watchlistOnly ? 'Pinned' : 'Preset'}
                tone="cyan"
                onClick={() => patchFilters({ ...defaultFilters, ...search.filters })}
                action={(
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      deleteSavedSearch(search.id)
                    }}
                    className="rounded-full border border-slate-700/80 px-2 py-1 text-[10px] text-slate-400 transition hover:border-rose-400/30 hover:text-rose-200"
                  >
                    Delete
                  </button>
                )}
              />
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Layer stack" subtitle="Operational overlays and intelligence feeds">
        <div className="grid grid-cols-3 gap-2">
          {LAYER_TOGGLES.map((layer) => (
            <ToggleTag key={layer.key} active={Boolean(activeLayers[layer.key])} onClick={() => toggleLayer(layer.key)}>
              {layer.label}
            </ToggleTag>
          ))}
        </div>
      </Panel>

      <Panel title="Priority feed" subtitle="Highest-risk contacts in the visible operating picture">
        <div className="space-y-2">
          {priorityFeed.map((vessel) => (
            <DataRow
              key={vessel.mmsi}
              title={vessel.name || `MMSI ${vessel.mmsi}`}
              subtitle={`${getVesselCategory(vessel)} · ${formatLastSeen(vessel)}`}
              value={`${vessel.intel.score}`}
              tone={vessel.intel.level === 'critical' ? 'rose' : vessel.intel.level === 'high' ? 'amber' : 'slate'}
              onClick={() => focusVessel(vessel)}
            />
          ))}
        </div>
      </Panel>

      <Panel title="Watchlist" subtitle="Pinned contacts for persistent surveillance">
        {watchlistVessels.length === 0 ? (
          <div className="text-sm text-slate-500">Pin a vessel from the search bar or the detail panel to keep it surfaced here.</div>
        ) : (
          <div className="space-y-2">
            {watchlistVessels.slice(0, 6).map((vessel) => (
              <DataRow
                key={vessel.mmsi}
                title={vessel.name || `MMSI ${vessel.mmsi}`}
                subtitle={`${getVesselCategory(vessel)} · ${formatLastSeen(vessel)}`}
                value={isDarkVessel(vessel) ? 'Dark' : 'Live'}
                tone={isDarkVessel(vessel) ? 'amber' : 'emerald'}
                onClick={() => focusVessel(vessel)}
              />
            ))}
          </div>
        )}
      </Panel>
    </div>
  )
}

function RangeField({ label, min, max, step, value, formatter, onChange }) {
  return (
    <label className="block rounded-2xl border border-slate-800/90 bg-slate-950/35 p-3">
      <div className="flex items-center justify-between gap-3">
        <span className="eyebrow-sm">{label}</span>
        <span className="text-xs font-mono text-slate-300">{formatter(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-3 w-full accent-cyan-400"
      />
    </label>
  )
}

function ToggleTag({ active, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-2xl border px-3 py-2 text-[11px] font-medium uppercase tracking-[0.16em] transition ${
        active
          ? 'border-cyan-400/25 bg-cyan-400/10 text-cyan-100'
          : 'border-slate-700/80 bg-slate-950/35 text-slate-400 hover:border-slate-500/60 hover:text-slate-200'
      }`}
    >
      {children}
    </button>
  )
}

function describeSavedSearch(filters) {
  const parts = []
  if (filters.searchQuery) parts.push(filters.searchQuery)
  if (filters.vesselCategories?.length) parts.push(filters.vesselCategories.join(', '))
  if (filters.watchlistOnly) parts.push('watchlist')
  if (filters.darkOnly) parts.push('dark only')
  if (filters.riskMinimum) parts.push(`risk ${filters.riskMinimum}+`)
  return parts.join(' · ') || 'General mission preset'
}
