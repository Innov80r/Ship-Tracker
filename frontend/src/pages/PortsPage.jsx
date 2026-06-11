import React, { useEffect, useMemo, useState } from 'react'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { DataRow, EmptyState, PageHeader, Panel, Pill, StatTile } from '../components/ui/CommandPrimitives'
import { createPortIcon } from '../utils/vesselIcons'
import { getApi } from '../utils/api'

const CATALOG_LIMIT = 3000

function normalizePortText(value) {
  return String(value || '').trim().toLowerCase()
}

function makeCatalogKey(port) {
  return String(port.id || `${normalizePortText(port.name)}:${normalizePortText(port.country)}`)
}

function makeHotspotKey(port) {
  return String(port.port_id || `${normalizePortText(port.port_name)}:${normalizePortText(port.country)}`)
}

function normalizeHotspotPort(port) {
  return {
    id: port.port_id || null,
    name: port.port_name,
    country: port.country,
    latitude: port.latitude,
    longitude: port.longitude,
    port_type: 'hotspot',
    un_locode: null,
    nearby_vessels: port.nearby_vessels || 0,
    queued_vessels: port.queued_vessels || 0,
    arrivals_per_hour: port.arrivals_per_hour || 0,
    congestion_score: port.congestion_score || 0,
  }
}

function getHotspotForCatalogPort(port, hotspotLookup) {
  if (!port) return null
  return hotspotLookup.get(makeCatalogKey(port))
    || hotspotLookup.get(`${normalizePortText(port.name)}:${normalizePortText(port.country)}`)
    || null
}

export default function PortsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [catalogPorts, setCatalogPorts] = useState([])
  const [hotspots, setHotspots] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedPortKey, setSelectedPortKey] = useState(null)

  useEffect(() => {
    let cancelled = false

    const loadPorts = async () => {
      setLoading(true)
      const [catalogResult, hotspotResult] = await Promise.allSettled([
        getApi('/api/ports', { params: { limit: CATALOG_LIMIT } }),
        getApi('/api/intel/ports/congestion', { params: { limit: 40 } }),
      ])

      if (cancelled) return

      setCatalogPorts(catalogResult.status === 'fulfilled' ? catalogResult.value.ports || [] : [])
      setHotspots(hotspotResult.status === 'fulfilled' ? hotspotResult.value.ports || [] : [])
      setLoading(false)
    }

    loadPorts()
    const intervalId = window.setInterval(loadPorts, 45000)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  const filteredCatalog = useMemo(() => {
    const query = normalizePortText(searchQuery)
    if (!query) return catalogPorts

    return catalogPorts.filter((port) => (
      `${port.name || ''} ${port.country || ''} ${port.un_locode || ''} ${port.port_type || ''}`
        .toLowerCase()
        .includes(query)
    ))
  }, [catalogPorts, searchQuery])

  const filteredHotspots = useMemo(() => {
    const query = normalizePortText(searchQuery)
    if (!query) return hotspots

    return hotspots.filter((port) => (
      `${port.port_name || ''} ${port.country || ''}`.toLowerCase().includes(query)
    ))
  }, [hotspots, searchQuery])

  const hotspotByCatalogKey = useMemo(() => {
    const lookup = new Map()
    filteredHotspots.forEach((port) => {
      lookup.set(makeHotspotKey(port), port)
      lookup.set(
        `${normalizePortText(port.port_name)}:${normalizePortText(port.country)}`,
        port,
      )
    })
    return lookup
  }, [filteredHotspots])

  const selectedCatalogPort = useMemo(() => {
    if (!selectedPortKey) return filteredCatalog[0] || null

    return filteredCatalog.find((port) => makeCatalogKey(port) === selectedPortKey)
      || filteredCatalog.find(
        (port) => `${normalizePortText(port.name)}:${normalizePortText(port.country)}` === selectedPortKey,
      )
      || null
  }, [filteredCatalog, selectedPortKey])

  const selectedHotspot = useMemo(() => {
    if (selectedCatalogPort) {
      return hotspotByCatalogKey.get(makeCatalogKey(selectedCatalogPort))
        || hotspotByCatalogKey.get(
          `${normalizePortText(selectedCatalogPort.name)}:${normalizePortText(selectedCatalogPort.country)}`,
        )
        || null
    }

    if (!selectedPortKey) return filteredHotspots[0] || null
    return hotspotByCatalogKey.get(selectedPortKey) || null
  }, [filteredHotspots, hotspotByCatalogKey, selectedCatalogPort, selectedPortKey])

  const selectedPort = selectedCatalogPort || (selectedHotspot ? normalizeHotspotPort(selectedHotspot) : null)

  const countriesRepresented = useMemo(() => {
    const countries = new Set()
    catalogPorts.forEach((port) => {
      if (port.country) countries.add(port.country)
    })
    return countries.size
  }, [catalogPorts])

  const metrics = useMemo(() => ({
    catalog: catalogPorts.length,
    countries: countriesRepresented,
    hotspots: hotspots.length,
    queued: hotspots.reduce((sum, port) => sum + (port.queued_vessels || 0), 0),
  }), [catalogPorts, countriesRepresented, hotspots])

  return (
    <div className="page-scroll" id="ports-page">
      <PageHeader
        eyebrow="Port intelligence"
        title="Global Port Catalog & Congestion"
        subtitle="Search the cached world port database, validate country coverage, and overlay live congestion hotspots from the backend intelligence engine."
        actions={(
          <>
            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="input-field w-72"
              placeholder="Search port, country, UN/LOCODE, type..."
            />
            <Pill tone="slate">{loading ? 'Refreshing' : `${catalogPorts.length} cached ports`}</Pill>
          </>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Catalog ports" value={metrics.catalog} caption="Ports cached from the global OSM-derived catalog" tone="cyan" />
        <StatTile label="Countries covered" value={metrics.countries} caption="Distinct countries represented in the current cache" tone="emerald" />
        <StatTile label="Hotspot ports" value={metrics.hotspots} caption="Ports currently ranked by congestion pressure" tone="amber" />
        <StatTile label="Queueing contacts" value={metrics.queued} caption="Vessels holding close to hotspot approaches" tone="rose" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Port theater" subtitle="Hotspot overlay with direct jump-to-port for the selected catalog entry">
          <div className="h-[32rem] overflow-hidden rounded-[1.5rem] border border-slate-800/90">
            <MapContainer center={[25, 0]} zoom={2} className="h-full w-full">
              <TileLayer
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                attribution="&copy; OSM &copy; CARTO"
              />
              <SelectedPortFocus port={selectedPort} />

              {filteredHotspots.map((port) => (
                <Marker
                  key={`hotspot-${makeHotspotKey(port)}`}
                  position={[port.latitude, port.longitude]}
                  icon={createPortIcon()}
                  eventHandlers={{
                    click: () => setSelectedPortKey(
                      `${normalizePortText(port.port_name)}:${normalizePortText(port.country)}`,
                    ),
                  }}
                >
                  <Popup>
                    <div className="text-xs">
                      <div className="font-semibold">{port.port_name}</div>
                      <div className="text-slate-400">{port.country || 'Unknown country'}</div>
                      <div className="mt-2 text-slate-300">Congestion score: {port.congestion_score}</div>
                      <div className="text-slate-500">{port.nearby_vessels} contacts · {port.queued_vessels} queueing</div>
                    </div>
                  </Popup>
                </Marker>
              ))}

              {selectedPort && (
                <Marker
                  key={`selected-${makeCatalogKey(selectedPort)}`}
                  position={[selectedPort.latitude, selectedPort.longitude]}
                  icon={createPortIcon()}
                >
                  <Popup>
                    <div className="text-xs">
                      <div className="font-semibold">{selectedPort.name}</div>
                      <div className="text-slate-400">
                        {selectedPort.country || 'Unknown country'}
                        {selectedPort.port_type ? ` · ${selectedPort.port_type}` : ''}
                      </div>
                      {selectedPort.un_locode && <div className="mt-2 text-slate-300">UN/LOCODE: {selectedPort.un_locode}</div>}
                    </div>
                  </Popup>
                </Marker>
              )}
            </MapContainer>
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel title="Selected port" subtitle="Catalog metadata plus live congestion context when available">
            {selectedPort ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Pill tone="cyan">{selectedPort.country || 'Unknown country'}</Pill>
                  {selectedPort.port_type && <Pill tone="slate">{selectedPort.port_type}</Pill>}
                  {selectedPort.un_locode && <Pill tone="emerald">{selectedPort.un_locode}</Pill>}
                  {selectedHotspot && <Pill tone="amber">Hotspot {selectedHotspot.congestion_score}</Pill>}
                </div>
                <div>
                  <div className="text-xl font-semibold text-white">{selectedPort.name}</div>
                  <div className="mt-1 text-sm text-slate-500">
                    {selectedPort.country || 'Unknown country'} · {selectedPort.latitude?.toFixed(3)}, {selectedPort.longitude?.toFixed(3)}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <PortMetric label="Nearby contacts" value={selectedHotspot?.nearby_vessels ?? '—'} />
                  <PortMetric label="Queueing" value={selectedHotspot?.queued_vessels ?? '—'} />
                  <PortMetric label="Arrivals/hr" value={selectedHotspot?.arrivals_per_hour ?? '—'} />
                  <PortMetric label="Congestion" value={selectedHotspot?.congestion_score ?? '—'} />
                </div>
              </div>
            ) : (
              <EmptyState title="No port selected" message="Search the catalog or pick a hotspot to inspect port metadata and live berth pressure." />
            )}
          </Panel>

          <Panel title="Hotspot ranking" subtitle="Ports with the highest current congestion score">
            {filteredHotspots.length === 0 ? (
              <EmptyState title="No hotspot ports" message="The backend congestion model has no current hotspot output for the active search scope." />
            ) : (
              <div className="space-y-2">
                {filteredHotspots.slice(0, 12).map((port) => (
                  <DataRow
                    key={makeHotspotKey(port)}
                    title={port.port_name}
                    subtitle={`${port.country || 'Unknown'} · ${port.nearby_vessels} contacts · ${port.queued_vessels} queueing`}
                    value={`Score ${port.congestion_score}`}
                    tone="amber"
                    onClick={() => setSelectedPortKey(
                      `${normalizePortText(port.port_name)}:${normalizePortText(port.country)}`,
                    )}
                  />
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>

      <Panel
        title="Port catalog"
        subtitle="Searchable catalog view. Selecting a row jumps the map to that port even if it is not currently congested."
      >
        {filteredCatalog.length === 0 ? (
          <EmptyState title="No ports matched" message="Try a different port name, country, UN/LOCODE, or type filter." />
        ) : (
          <div className="space-y-2">
            {filteredCatalog.slice(0, 120).map((port) => (
              <DataRow
                key={makeCatalogKey(port)}
                title={port.name}
                subtitle={`${port.country || 'Unknown country'} · ${port.un_locode || 'No UN/LOCODE'} · ${port.port_type || 'port'}`}
                value={getHotspotForCatalogPort(port, hotspotByCatalogKey) ? 'Hotspot' : 'Catalog'}
                tone={getHotspotForCatalogPort(port, hotspotByCatalogKey) ? 'amber' : 'slate'}
                onClick={() => setSelectedPortKey(makeCatalogKey(port))}
              />
            ))}
          </div>
        )}
      </Panel>
    </div>
  )
}

function SelectedPortFocus({ port }) {
  const map = useMap()

  useEffect(() => {
    if (port?.latitude == null || port?.longitude == null) return
    map.flyTo([port.latitude, port.longitude], Math.max(map.getZoom(), 6), {
      animate: true,
      duration: 1.1,
    })
  }, [map, port])

  return null
}

function PortMetric({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-800/90 bg-slate-950/35 p-3">
      <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-white">{value}</div>
    </div>
  )
}
