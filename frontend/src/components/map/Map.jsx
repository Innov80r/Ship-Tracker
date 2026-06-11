import React, { useEffect, useMemo, useRef, useState } from 'react'
import { CircleMarker, GeoJSON, MapContainer, Marker, Polyline, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { useShallow } from 'zustand/react/shallow'
import useVesselStore from '../../store/vesselStore'
import useMapStore from '../../store/mapStore'
import useUIStore from '../../store/uiStore'
import useFilterStore, { selectFilterSnapshot } from '../../store/filterStore'
import useIntelStore from '../../store/intelStore'
import { createIncidentIcon, createPortIcon } from '../../utils/vesselIcons'
import { getStatusColor, getVesselColor } from '../../utils/vesselColors'
import useVesselTrail from '../../hooks/useVesselTrail'
import usePorts from '../../hooks/usePorts'
import useCountryCatalog from '../../hooks/useCountryCatalog'
import useIncidents from '../../hooks/useIncidents'
import useZones from '../../hooks/useZones'
import useWeather from '../../hooks/useWeather'
import useLayerGeoJson from '../../hooks/useLayerGeoJson'
import { filterVessels, getProjectedRoute } from '../../utils/intel'
import { buildCountryDirectory, filterPortsByCountry, filterVesselsByCountry } from '../../utils/countryMode'
import { samplePortsForViewport } from '../../utils/geoHelpers'

import 'leaflet.heat'

const OPEN_SEA_MAP_TILE_URLS = [
  'https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png',
  'https://t1.openseamap.org/seamark/{z}/{x}/{y}.png',
  'https://t2.openseamap.org/seamark/{z}/{x}/{y}.png',
]

function isSameView(map, center, zoom) {
  const current = map.getCenter()
  return (
    Math.abs(current.lat - center[0]) < 0.000001 &&
    Math.abs(current.lng - center[1]) < 0.000001 &&
    map.getZoom() === zoom
  )
}

function destinationPoint(lat, lon, bearingDegrees, distanceNm) {
  const earthRadiusNm = 3440.065
  const angularDistance = distanceNm / earthRadiusNm
  const bearing = bearingDegrees * Math.PI / 180
  const startLat = lat * Math.PI / 180
  const startLon = lon * Math.PI / 180

  const endLat = Math.asin(
    Math.sin(startLat) * Math.cos(angularDistance) +
    Math.cos(startLat) * Math.sin(angularDistance) * Math.cos(bearing)
  )

  const endLon = startLon + Math.atan2(
    Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(startLat),
    Math.cos(angularDistance) - Math.sin(startLat) * Math.sin(endLat)
  )

  return [
    endLat * 180 / Math.PI,
    ((endLon * 180 / Math.PI + 540) % 360) - 180,
  ]
}

function getWaveColor(height) {
  if (height == null) return '#38bdf8'
  if (height < 1) return '#22d3ee'
  if (height < 2.5) return '#10b981'
  if (height < 4) return '#f59e0b'
  return '#f43f5e'
}

function getTideColor(level) {
  if (level == null) return '#94a3b8'
  if (level >= 3) return '#22d3ee'
  if (level >= 1.5) return '#10b981'
  if (level >= 0) return '#f59e0b'
  return '#f43f5e'
}

function VesselLayer({ vessels }) {
  const selectVessel = useVesselStore(s => s.selectVessel)
  const openVesselPanel = useUIStore(s => s.openVesselPanel)
  const map = useMap()
  const rendererRef = useRef(null)
  const layerGroupRef = useRef(null)
  const vesselLookupRef = useRef({})
  const markersRef = useRef({})
  const markerStateRef = useRef({})

  useEffect(() => {
    vesselLookupRef.current = Object.fromEntries(vessels.map((vessel) => [String(vessel.mmsi), vessel]))
  }, [vessels])

  useEffect(() => {
    rendererRef.current = L.canvas({ padding: 0.5 })
    const layerGroup = L.layerGroup()
    layerGroupRef.current = layerGroup
    map.addLayer(layerGroup)

    return () => {
      map.removeLayer(layerGroup)
      layerGroupRef.current = null
      rendererRef.current = null
      markersRef.current = {}
      markerStateRef.current = {}
    }
  }, [map])

  useEffect(() => {
    const syncMarkerStyles = () => {
      const zoom = map.getZoom()
      Object.entries(markersRef.current).forEach(([markerKey, marker]) => {
        const vessel = vesselLookupRef.current[markerKey]
        if (!vessel) return
        marker.setStyle(getVesselStyle(vessel, zoom))
      })
    }

    map.on('zoomend', syncMarkerStyles)
    return () => {
      map.off('zoomend', syncMarkerStyles)
    }
  }, [map])

  useEffect(() => {
    if (!layerGroupRef.current || !rendererRef.current) return

    const vesselArr = vessels
    const zoom = map.getZoom()
    const currentMMSIs = new Set(
      vesselArr
        .filter(v => v.latitude != null && v.longitude != null)
        .map(v => String(v.mmsi))
    )

    // Remove stale markers
    Object.keys(markersRef.current).forEach(mmsi => {
      if (!currentMMSIs.has(mmsi)) {
        layerGroupRef.current.removeLayer(markersRef.current[mmsi])
        delete markersRef.current[mmsi]
        delete markerStateRef.current[mmsi]
      }
    })

    // Add/update markers
    vesselArr.forEach(v => {
      const markerKey = String(v.mmsi)
      const existing = markersRef.current[markerKey]

      if (v.latitude == null || v.longitude == null) {
        if (existing) {
          layerGroupRef.current.removeLayer(existing)
          delete markersRef.current[markerKey]
          delete markerStateRef.current[markerKey]
        }
        return
      }

      const nextMarkerState = {
        positionKey: `${v.latitude}:${v.longitude}`,
        styleKey: `${v.nav_status ?? ''}:${v.vessel_type ?? ''}:${zoom}`,
      }

      if (existing) {
        const prevMarkerState = markerStateRef.current[markerKey]

        if (!prevMarkerState || prevMarkerState.positionKey !== nextMarkerState.positionKey) {
          existing.setLatLng([v.latitude, v.longitude])
        }

        if (!prevMarkerState || prevMarkerState.styleKey !== nextMarkerState.styleKey) {
          existing.setStyle(getVesselStyle(v, zoom))
        }

        markerStateRef.current[markerKey] = nextMarkerState
      } else {
        const marker = L.circleMarker([v.latitude, v.longitude], {
          ...getVesselStyle(v, zoom),
          renderer: rendererRef.current,
          pane: 'markerPane',
        })
        marker.on('click', () => {
          selectVessel(v.mmsi)
          openVesselPanel()
        })
        layerGroupRef.current.addLayer(marker)
        markersRef.current[markerKey] = marker
        markerStateRef.current[markerKey] = nextMarkerState
      }
    })
  }, [map, vessels, openVesselPanel, selectVessel])

  return null
}

function getVesselStyle(vessel, zoom) {
  const radius = zoom >= 8 ? 6 : zoom >= 6 ? 4.5 : zoom >= 4 ? 3.25 : 2.4

  return {
    radius,
    color: getStatusColor(vessel.nav_status),
    weight: zoom >= 6 ? 1.2 : 1,
    opacity: 0.95,
    fillColor: getVesselColor(vessel.vessel_type),
    fillOpacity: zoom >= 6 ? 0.92 : 0.8,
  }
}

function MapSync() {
  const center = useMapStore(s => s.center)
  const zoom = useMapStore(s => s.zoom)
  const map = useMap()
  const syncingFromStoreRef = useRef(false)

  useEffect(() => {
    if (isSameView(map, center, zoom)) return
    syncingFromStoreRef.current = true
    map.setView(center, zoom, { animate: true, duration: 1.0 })
  }, [center[0], center[1], map, zoom])

  useMapEvents({
    moveend: () => {
      if (syncingFromStoreRef.current) {
        syncingFromStoreRef.current = false
        return
      }

      const c = map.getCenter()
      const nextZoom = map.getZoom()
      const state = useMapStore.getState()
      const currentCenter = state.center

      if (
        Math.abs(currentCenter[0] - c.lat) < 0.000001 &&
        Math.abs(currentCenter[1] - c.lng) < 0.000001 &&
        state.zoom === nextZoom
      ) {
        return
      }

      useMapStore.setState({ center: [c.lat, c.lng], zoom: nextZoom })
    },
  })

  return null
}

function MapResizeFix() {
  const map = useMap()

  useEffect(() => {
    let frameId = 0
    let timeoutId = 0

    const invalidate = () => {
      map.invalidateSize({ animate: false })
    }

    frameId = window.requestAnimationFrame(invalidate)
    timeoutId = window.setTimeout(invalidate, 180)

    let observer = null
    const container = map.getContainer()
    if (typeof ResizeObserver !== 'undefined' && container) {
      observer = new ResizeObserver(() => {
        invalidate()
      })
      observer.observe(container)
    }

    return () => {
      window.cancelAnimationFrame(frameId)
      window.clearTimeout(timeoutId)
      observer?.disconnect()
    }
  }, [map])

  return null
}

function HeatmapLayer({ vessels }) {
  const map = useMap()
  const heatmapRef = useRef(null)

  useEffect(() => {
    const heatLayer = L.heatLayer([], {
      radius: 22,
      blur: 16,
      maxZoom: 8,
      gradient: {
        0.2: '#22d3ee',
        0.45: '#10b981',
        0.7: '#f59e0b',
        1.0: '#f43f5e',
      },
    })
    heatmapRef.current = heatLayer
    map.addLayer(heatLayer)

    return () => {
      map.removeLayer(heatLayer)
      heatmapRef.current = null
    }
  }, [map])

  useEffect(() => {
    if (!heatmapRef.current) return

    const points = vessels
      .filter(v => v.latitude != null && v.longitude != null)
      .slice(0, 2500)
      .map(v => [v.latitude, v.longitude, Math.max(0.2, Math.min((v.speed || 0) / 25, 1))])

    heatmapRef.current.setLatLngs(points)
  }, [vessels])

  return null
}

function SelectedVesselTrailLayer() {
  const selectedVessel = useVesselStore(s => s.selectedVessel)
  const vesselPanelOpen = useUIStore(s => s.vesselPanelOpen)
  const trailsEnabled = useMapStore(s => s.activeLayers.trails)
  const showTrail = Boolean(selectedVessel?.mmsi) && (vesselPanelOpen || trailsEnabled)
  const trail = useVesselTrail(selectedVessel?.mmsi, showTrail, 180)

  if (!showTrail || trail.length < 2) return null

  return (
    <Polyline
      positions={trail}
      pathOptions={{
        color: '#22d3ee',
        weight: 3,
        opacity: 0.8,
        dashArray: '8 6',
      }}
    />
  )
}

function ProjectedRouteLayer() {
  const selectedVessel = useVesselStore((state) => state.selectedVessel)
  const projectedRoute = useMemo(() => getProjectedRoute(selectedVessel), [selectedVessel])

  if (projectedRoute.length < 2) return null

  return (
    <Polyline
      positions={projectedRoute}
      pathOptions={{
        color: '#7dd3fc',
        weight: 2.5,
        opacity: 0.8,
        dashArray: '4 8',
      }}
    />
  )
}

function PortsLayer({ country }) {
  const { ports } = usePorts(true)
  const map = useMap()
  const [boundsSnapshot, setBoundsSnapshot] = useState(() => map.getBounds())

  useMapEvents({
    moveend: () => {
      setBoundsSnapshot(map.getBounds())
    },
    zoomend: () => {
      setBoundsSnapshot(map.getBounds())
    },
  })

  const visiblePorts = useMemo(() => {
    const paddedBounds = boundsSnapshot?.pad(0.25)
    if (!paddedBounds) return []
    const portLimit = country ? 5000 : map.getZoom() >= 6 ? 3000 : 1500
    const cellSizeDegrees = country ? 4 : map.getZoom() >= 6 ? 3 : map.getZoom() >= 4 ? 7 : 14

    const inBoundsPorts = filterPortsByCountry(
      ports.filter(port => port.latitude != null && port.longitude != null),
      country
    )
      .filter(port => paddedBounds.contains([port.latitude, port.longitude]))

    return samplePortsForViewport(inBoundsPorts, portLimit, cellSizeDegrees)
  }, [boundsSnapshot, country, map, ports])

  return visiblePorts
    .map(port => (
      <Marker
        key={port.id || `${port.name}-${port.latitude}-${port.longitude}`}
        position={[port.latitude, port.longitude]}
        icon={createPortIcon()}
      >
        <Popup>
          <div className="text-xs">
            <div className="font-semibold">{port.name}</div>
            <div className="text-slate-400">{port.country || 'Unknown country'}{port.port_type ? ` · ${port.port_type}` : ''}</div>
          </div>
        </Popup>
      </Marker>
    ))
}

function SelectedCountryLayer({ country }) {
  if (!country?.features?.length) return null

  return country.features.map((feature, index) => (
    <GeoJSON
      key={`${country.key}-${index}`}
      data={feature}
      style={{
        color: '#22d3ee',
        weight: 2.2,
        opacity: 0.9,
        fillColor: '#22d3ee',
        fillOpacity: 0.06,
        dashArray: '8 6',
      }}
    />
  ))
}

function IncidentsLayer() {
  const { incidents } = useIncidents(false)

  return incidents
    .filter(incident => incident.latitude != null && incident.longitude != null)
    .map(incident => (
      <Marker
        key={incident.id || `${incident.mmsi}-${incident.detected_at}`}
        position={[incident.latitude, incident.longitude]}
        icon={createIncidentIcon()}
      >
        <Popup>
          <div className="text-xs">
            <div className="font-semibold">{incident.incident_type}</div>
            <div className="text-slate-300">{incident.vessel_name || `MMSI ${incident.mmsi}`}</div>
            <div className="text-slate-500">{incident.description || 'No description available'}</div>
          </div>
        </Popup>
      </Marker>
    ))
}

function ZonesLayer() {
  const { zones } = useZones(true)

  return zones
    .filter(zone => zone.geometry)
    .map(zone => (
      <GeoJSON
        key={zone.id}
        data={zone.geometry}
        style={{
          color: zone.zone_type === 'restricted' ? '#f43f5e' : '#f59e0b',
          weight: 2,
          fillOpacity: 0.12,
        }}
        onEachFeature={(_, layer) => {
          layer.bindPopup(`<strong>${zone.name}</strong><br/>${zone.zone_type}`)
        }}
      />
    ))
}

function WindLayer({ weather }) {
  return weather
    .filter(point => point.lat != null && point.lon != null && point.wind_speed != null)
    .map(point => (
      <CircleMarker
        key={`wind-${point.lat}-${point.lon}`}
        center={[point.lat, point.lon]}
        radius={Math.max(4, Math.min((point.wind_speed || 0) / 2.5, 11))}
        pathOptions={{
          color: '#22d3ee',
          fillColor: '#22d3ee',
          fillOpacity: 0.25,
          weight: 1,
        }}
      >
        <Popup>
          <div className="text-xs">
            <div className="font-semibold">Wind sample</div>
            <div className="text-slate-300">{point.wind_speed ?? '—'} km/h</div>
            <div className="text-slate-500">{point.wind_direction ?? '—'}°</div>
          </div>
        </Popup>
      </CircleMarker>
    ))
}

function WaveLayer({ weather }) {
  return weather
    .filter(point => point.lat != null && point.lon != null && point.wave_height != null)
    .map(point => {
      const color = getWaveColor(point.wave_height)
      return (
        <CircleMarker
          key={`wave-${point.lat}-${point.lon}`}
          center={[point.lat, point.lon]}
          radius={Math.max(4, Math.min((point.wave_height || 0) * 2.6, 12))}
          pathOptions={{
            color,
            fillColor: color,
            fillOpacity: 0.22,
            weight: 1.2,
          }}
        >
          <Popup>
            <div className="text-xs">
              <div className="font-semibold">Wave sample</div>
              <div className="text-slate-300">Height: {point.wave_height ?? '—'} m</div>
              <div className="text-slate-500">Period: {point.wave_period ?? '—'} s</div>
              <div className="text-slate-500">Direction: {point.wave_direction ?? '—'}°</div>
            </div>
          </Popup>
        </CircleMarker>
      )
    })
}

function CurrentLayer({ weather }) {
  return weather
    .filter(point => point.lat != null && point.lon != null && point.current_speed != null && point.current_direction != null)
    .flatMap(point => {
      const lineEnd = destinationPoint(
        point.lat,
        point.lon,
        point.current_direction,
        Math.max(40, Math.min((point.current_speed || 0) * 55, 120))
      )

      return [
        <Polyline
          key={`current-line-${point.lat}-${point.lon}`}
          positions={[[point.lat, point.lon], lineEnd]}
          pathOptions={{
            color: '#34d399',
            weight: 2,
            opacity: 0.75,
          }}
        >
          <Popup>
            <div className="text-xs">
              <div className="font-semibold">Current vector</div>
              <div className="text-slate-300">Speed: {point.current_speed ?? '—'} m/s</div>
              <div className="text-slate-500">Direction: {point.current_direction ?? '—'}°</div>
            </div>
          </Popup>
        </Polyline>,
        <CircleMarker
          key={`current-dot-${point.lat}-${point.lon}`}
          center={lineEnd}
          radius={2.5}
          pathOptions={{
            color: '#34d399',
            fillColor: '#34d399',
            fillOpacity: 0.9,
            weight: 1,
          }}
        />,
      ]
    })
}

function TideLayer({ tides }) {
  return tides
    .filter(point => point.latitude != null && point.longitude != null)
    .map(point => {
      const color = getTideColor(point.water_level)
      const isGlobalGrid = point.source === 'open-meteo'
      return (
        <CircleMarker
          key={`tide-${point.station_id}`}
          center={[point.latitude, point.longitude]}
          radius={Math.max(5, Math.min(Math.abs(point.water_level || 0) * 2 + 5, 11))}
          pathOptions={{
            color,
            fillColor: color,
            fillOpacity: 0.28,
            weight: 1.5,
          }}
        >
          <Popup>
            <div className="text-xs">
              <div className="font-semibold">{point.station_name}</div>
              <div className="text-slate-400">{isGlobalGrid ? 'Global sea-level sample' : 'NOAA tide station'}</div>
              <div className="text-slate-300">Water level: {point.water_level ?? '—'} ft</div>
              <div className="text-slate-500">{point.time || 'No timestamp'}</div>
            </div>
          </Popup>
        </CircleMarker>
      )
    })
}

function GeoJsonLayer({ path, style, popupLabel }) {
  const geojson = useLayerGeoJson(path, true)

  if (!geojson?.features?.length) return null

  return (
    <GeoJSON
      data={geojson}
      style={style}
      onEachFeature={(feature, layer) => {
        const title = feature?.properties?.name || feature?.properties?.NAME || popupLabel
        if (title) layer.bindPopup(String(title))
      }}
    />
  )
}

function NauticalChartLayer() {
  const [providerIndex, setProviderIndex] = useState(0)
  const tileUrl = OPEN_SEA_MAP_TILE_URLS[providerIndex]

  return (
    <TileLayer
      key={tileUrl}
      url={tileUrl}
      opacity={0.95}
      maxZoom={18}
      zIndex={320}
      attribution='&copy; <a href="https://www.openseamap.org/">OpenSeaMap</a> contributors'
      eventHandlers={{
        tileerror: () => {
          setProviderIndex((currentIndex) => {
            if (currentIndex >= OPEN_SEA_MAP_TILE_URLS.length - 1) {
              return currentIndex
            }
            return currentIndex + 1
          })
        },
      }}
    />
  )
}

export default function Map() {
  const vesselsMap = useVesselStore((state) => state.vessels)
  const vessels = useMemo(() => Object.values(vesselsMap), [vesselsMap])
  const activeLayers = useMapStore(s => s.activeLayers)
  const selectedCountryKey = useMapStore((state) => state.selectedCountryKey)
  const filters = useFilterStore(useShallow(selectFilterSnapshot))
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const environmentEnabled = activeLayers.weather || activeLayers.waves || activeLayers.currents || activeLayers.tides
  const { weather, tides } = useWeather(environmentEnabled)
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
  const nauticalChartsEnabled = activeLayers.openSeaMap
  const visibleVessels = useMemo(() => {
    const baseVessels = filterVessels(vessels, filters, watchlistMmsis)
    return selectedCountry ? filterVesselsByCountry(baseVessels, selectedCountry) : baseVessels
  }, [vessels, filters, watchlistMmsis, selectedCountry])

  return (
    <MapContainer
      center={[30, 0]}
      zoom={3}
      minZoom={2}
      worldCopyJump={true}
      className="w-full h-full"
      zoomControl={true}
      attributionControl={true}
      id="main-map"
    >
      {/* OpenSeaMap is only seamarks, so use a readable light basemap when nautical charts are enabled. */}
      {nauticalChartsEnabled ? (
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          maxZoom={19}
        />
      ) : (
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
          maxZoom={19}
        />
      )}

      {/* OpenSeaMap nautical overlay */}
      {nauticalChartsEnabled && <NauticalChartLayer />}

      {/* EMODnet Bathymetry */}
      {activeLayers.bathymetry && (
        <TileLayer
          url="https://tiles.emodnet-bathymetry.eu/2020/baselayer/web_mercator/{z}/{x}/{y}.png"
          opacity={0.5}
          maxZoom={10}
        />
      )}

      {/* Vessel markers via cluster layer */}
      {activeLayers.vessels && <VesselLayer vessels={visibleVessels} />}
      {activeLayers.heatmap && <HeatmapLayer vessels={visibleVessels} />}
      <SelectedVesselTrailLayer />
      <ProjectedRouteLayer />
      <SelectedCountryLayer country={selectedCountry} />
      {activeLayers.ports && <PortsLayer country={selectedCountry} />}
      {activeLayers.incidents && <IncidentsLayer />}
      {activeLayers.zones && <ZonesLayer />}
      {activeLayers.weather && <WindLayer weather={weather} />}
      {activeLayers.waves && <WaveLayer weather={weather} />}
      {activeLayers.currents && <CurrentLayer weather={weather} />}
      {activeLayers.tides && <TideLayer tides={tides} />}
      {activeLayers.cables && (
        <GeoJsonLayer
          path="/api/layers/cables"
          popupLabel="Submarine cable"
          style={{ color: '#f59e0b', weight: 1.2, opacity: 0.7 }}
        />
      )}
      {activeLayers.shippingLanes && (
        <GeoJsonLayer
          path="/api/layers/shipping-lanes"
          popupLabel="Shipping lane"
          style={{ color: '#fb7185', weight: 1.5, opacity: 0.65, dashArray: '10 6' }}
        />
      )}
      {activeLayers.eez && (
        <GeoJsonLayer
          path="/api/layers/eez"
          popupLabel="EEZ boundary"
          style={{ color: '#38bdf8', weight: 1.2, opacity: 0.65, dashArray: '6 4', fillOpacity: 0 }}
        />
      )}

      {/* Map sync with store */}
      <MapResizeFix />
      <MapSync />
    </MapContainer>
  )
}
