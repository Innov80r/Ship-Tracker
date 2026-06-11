import React, { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, Marker, Polyline, Popup, TileLayer } from 'react-leaflet'
import useHistory from '../hooks/useHistory'
import { PageHeader, Panel, Pill, StatTile } from '../components/ui/CommandPrimitives'
import { exportAsCSV, exportAsGPX } from '../utils/exportHelpers'
import { formatDuration, formatTimestamp } from '../utils/formatters'
import { getApi } from '../utils/api'

export default function HistoryPage() {
  const { track, events, routePrediction, loading, loadHistory } = useHistory()
  const [primaryMmsi, setPrimaryMmsi] = useState('')
  const [secondaryMmsi, setSecondaryMmsi] = useState('')
  const [secondaryTrack, setSecondaryTrack] = useState([])
  const [secondaryLoading, setSecondaryLoading] = useState(false)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [playbackIndex, setPlaybackIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speedMultiplier, setSpeedMultiplier] = useState(1)

  const primaryPositions = track.filter((point) => point.latitude != null && point.longitude != null).map((point) => [point.latitude, point.longitude])
  const secondaryPositions = secondaryTrack.filter((point) => point.latitude != null && point.longitude != null).map((point) => [point.latitude, point.longitude])
  const projectedRoutePositions = (routePrediction?.projected_route || [])
    .filter((point) => point.latitude != null && point.longitude != null)
    .map((point) => [point.latitude, point.longitude])
  const maxIndex = Math.max(track.length, secondaryTrack.length, 1) - 1

  useEffect(() => {
    if (!playing || maxIndex <= 0) return
    const interval = window.setInterval(() => {
      setPlaybackIndex((current) => (current >= maxIndex ? 0 : current + 1))
    }, Math.max(180, 700 / speedMultiplier))
    return () => window.clearInterval(interval)
  }, [maxIndex, playing, speedMultiplier])

  useEffect(() => {
    setPlaybackIndex(0)
    setPlaying(false)
  }, [track.length, secondaryTrack.length])

  const handleSearch = async () => {
    if (!primaryMmsi) return
    await loadHistory(primaryMmsi, startDate || undefined, endDate || undefined)

    if (!secondaryMmsi) {
      setSecondaryTrack([])
      return
    }

    setSecondaryLoading(true)
    try {
      const params = {}
      if (startDate) params.start = startDate
      if (endDate) params.end = endDate
      const data = await getApi(`/api/history/${secondaryMmsi}`, { params })
      setSecondaryTrack(data.points || [])
    } catch {
      setSecondaryTrack([])
    } finally {
      setSecondaryLoading(false)
    }
  }

  const primaryCurrent = track[Math.min(playbackIndex, Math.max(track.length - 1, 0))]
  const secondaryCurrent = secondaryTrack[Math.min(playbackIndex, Math.max(secondaryTrack.length - 1, 0))]

  return (
    <div className="page-scroll" id="history-page">
      <PageHeader
        eyebrow="Playback"
        title="Timeline & Replay"
        subtitle="Replay a vessel track, compare two contacts on the same timeline, inspect backend playback events, and review route projection with ETA."
        actions={(
          <>
            {track.length > 0 && <button type="button" className="btn-ghost" onClick={() => exportAsCSV(track, `track_${primaryMmsi}.csv`)}>Export CSV</button>}
            {track.length > 0 && <button type="button" className="btn-primary" onClick={() => exportAsGPX(track, `Vessel ${primaryMmsi}`, `track_${primaryMmsi}.gpx`)}>Export GPX</button>}
          </>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Primary points" value={track.length} caption="Track points loaded for primary vessel" tone="cyan" />
        <StatTile label="Compare points" value={secondaryTrack.length} caption="Track points loaded for secondary vessel" tone="emerald" />
        <StatTile label="Playback events" value={events.length} caption="Derived gaps and motion events from backend" tone="amber" />
        <StatTile label="ETA" value={routePrediction?.eta_hours != null ? formatDuration(routePrediction.eta_hours) : '—'} caption="Destination-aware ETA when a known port is matched" tone="rose" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="Replay controls" subtitle="Load one or two tracks and scrub them on a shared timeline">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Primary MMSI" value={primaryMmsi} onChange={setPrimaryMmsi} placeholder="211234567" />
            <Field label="Compare MMSI" value={secondaryMmsi} onChange={setSecondaryMmsi} placeholder="Optional" />
            <Field label="From" type="datetime-local" value={startDate} onChange={setStartDate} />
            <Field label="To" type="datetime-local" value={endDate} onChange={setEndDate} />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button type="button" className="btn-primary" onClick={handleSearch} disabled={loading || secondaryLoading}>
              {loading || secondaryLoading ? 'Loading…' : 'Load replay'}
            </button>
            <button type="button" className="btn-ghost" onClick={() => setPlaying((state) => !state)} disabled={track.length === 0}>
              {playing ? 'Pause' : 'Play'}
            </button>
            <button type="button" className="btn-ghost" onClick={() => setPlaybackIndex(0)} disabled={track.length === 0}>
              Reset
            </button>
            <Pill tone="slate">{speedMultiplier}x</Pill>
            <input
              type="range"
              min={1}
              max={4}
              step={1}
              value={speedMultiplier}
              onChange={(event) => setSpeedMultiplier(Number(event.target.value))}
              className="w-32 accent-cyan-400"
            />
          </div>
          <div className="mt-4 rounded-2xl border border-slate-800/90 bg-slate-950/35 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="eyebrow-sm">Timeline index</span>
              <span className="font-mono text-xs text-slate-400">{playbackIndex + 1}/{maxIndex + 1}</span>
            </div>
            <input
              type="range"
              min={0}
              max={maxIndex}
              value={Math.min(playbackIndex, maxIndex)}
              onChange={(event) => setPlaybackIndex(Number(event.target.value))}
              className="mt-4 w-full accent-cyan-400"
            />
          </div>
        </Panel>

        <Panel title="Route projection" subtitle="Projected route steps and ETA from the backend intelligence service">
          {!routePrediction || routePrediction.error ? (
            <div className="text-sm text-slate-500">Load a primary vessel to see route projection and ETA data.</div>
          ) : (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Pill tone="cyan">{routePrediction.projected_route?.length || 0} projected steps</Pill>
                <Pill tone="amber">{routePrediction.destination || 'No destination'}</Pill>
                <Pill tone={routePrediction.eta_hours != null ? 'rose' : 'slate'}>
                  {routePrediction.eta_hours != null ? formatDuration(routePrediction.eta_hours) : 'ETA unavailable'}
                </Pill>
              </div>
              <div className="rounded-2xl border border-slate-800/90 bg-slate-950/35 p-4">
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Matched port</div>
                <div className="mt-2 text-lg font-semibold text-white">
                  {routePrediction.matched_port?.name || 'No port match'}
                </div>
                <div className="mt-1 text-sm text-slate-400">
                  {routePrediction.matched_port?.country || 'Destination string did not resolve to a known port.'}
                </div>
              </div>
              <div className="space-y-2">
                {(routePrediction.projected_route || []).slice(0, 5).map((point) => (
                  <div key={point.step} className="intel-row">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-white">Projection +{point.minutes_ahead} min</div>
                      <div className="mt-1 truncate text-xs text-slate-500">{point.latitude.toFixed(3)}, {point.longitude.toFixed(3)}</div>
                    </div>
                    <Pill tone="violet">{Math.round(point.heading)}°</Pill>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel title="Playback events" subtitle="Course changes, AIS gaps, and motion markers from the backend event builder">
          {events.length === 0 ? (
            <div className="text-sm text-slate-500">Load a track to see replay event markers.</div>
          ) : (
            <div className="space-y-2">
              {events.map((event, index) => (
                <div key={`${event.type}-${event.timestamp}-${index}`} className="intel-row">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{formatEventLabel(event.type)}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">{formatEventDetail(event.details)}</div>
                  </div>
                  <Pill tone={event.type === 'ais_gap' ? 'amber' : 'cyan'}>{formatTimestamp(event.timestamp)}</Pill>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Replay map" subtitle="Primary and compare tracks synced to one timeline frame, with projected route overlay">
          <div className="h-[34rem] overflow-hidden rounded-[1.5rem] border border-slate-800/90">
            <MapContainer center={[30, 0]} zoom={3} className="h-full w-full">
              <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution='&copy; OSM &copy; CARTO' />
              {primaryPositions.length > 0 && (
                <>
                  <Polyline positions={primaryPositions} pathOptions={{ color: '#38bdf8', weight: 3, opacity: 0.9, dashArray: '8 4' }} />
                  {primaryCurrent?.latitude != null && primaryCurrent?.longitude != null && (
                    <CircleMarker center={[primaryCurrent.latitude, primaryCurrent.longitude]} radius={7} pathOptions={{ color: '#38bdf8', fillColor: '#38bdf8', fillOpacity: 0.9 }}>
                      <Popup>Primary replay frame: {formatTimestamp(primaryCurrent.timestamp)}</Popup>
                    </CircleMarker>
                  )}
                  {primaryPositions[0] && (
                    <Marker position={primaryPositions[0]}>
                      <Popup>Primary start</Popup>
                    </Marker>
                  )}
                </>
              )}

              {secondaryPositions.length > 0 && (
                <>
                  <Polyline positions={secondaryPositions} pathOptions={{ color: '#34d399', weight: 3, opacity: 0.85, dashArray: '3 6' }} />
                  {secondaryCurrent?.latitude != null && secondaryCurrent?.longitude != null && (
                    <CircleMarker center={[secondaryCurrent.latitude, secondaryCurrent.longitude]} radius={7} pathOptions={{ color: '#34d399', fillColor: '#34d399', fillOpacity: 0.9 }}>
                      <Popup>Compare replay frame: {formatTimestamp(secondaryCurrent.timestamp)}</Popup>
                    </CircleMarker>
                  )}
                </>
              )}

              {projectedRoutePositions.length > 1 && (
                <Polyline positions={projectedRoutePositions} pathOptions={{ color: '#8b5cf6', weight: 3, opacity: 0.8, dashArray: '4 8' }} />
              )}
            </MapContainer>
          </div>
        </Panel>
      </div>
    </div>
  )
}

function Field({ label, value, onChange, placeholder = '', type = 'text' }) {
  return (
    <label className="block">
      <div className="eyebrow-sm">{label}</div>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="input-field mt-2 w-full"
      />
    </label>
  )
}

function formatEventLabel(eventType) {
  if (eventType === 'track_start') return 'Track start'
  if (eventType === 'track_end') return 'Track end'
  if (eventType === 'ais_gap') return 'AIS gap'
  if (eventType === 'course_change') return 'Course change'
  if (eventType === 'speed_change') return 'Speed change'
  return eventType
}

function formatEventDetail(details = {}) {
  if (details.gap_minutes != null) return `${Math.round(details.gap_minutes)} minute telemetry gap`
  if (details.turn_degrees != null) return `${Math.round(details.turn_degrees)}° turn`
  if (details.from_speed != null && details.to_speed != null) return `${details.from_speed.toFixed(1)} kn to ${details.to_speed.toFixed(1)} kn`
  return 'Motion event'
}
