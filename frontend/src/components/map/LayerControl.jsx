import React, { useEffect } from 'react'
import { createPortal } from 'react-dom'
import useMapStore from '../../store/mapStore'

const LAYERS = [
  { key: 'vessels', label: 'Vessels', group: 'Core', supported: true },
  { key: 'openSeaMap', label: 'Nautical Charts', group: 'Core', supported: true },
  { key: 'bathymetry', label: 'Bathymetry', group: 'Core', supported: true },
  { key: 'heatmap', label: 'Density Heatmap', group: 'Vessels', supported: true },
  { key: 'trails', label: 'Vessel Trails', group: 'Vessels', supported: true },
  { key: 'weather', label: 'Wind Samples', group: 'Environment', supported: true },
  { key: 'waves', label: 'Waves', group: 'Environment', supported: true },
  { key: 'currents', label: 'Currents', group: 'Environment', supported: true },
  { key: 'tides', label: 'Tides', group: 'Environment', supported: true },
  { key: 'cables', label: 'Submarine Cables', group: 'Infrastructure', supported: true },
  { key: 'eez', label: 'EEZ Boundaries', group: 'Boundaries', supported: true },
  { key: 'shippingLanes', label: 'Shipping Lanes', group: 'Infrastructure', supported: true },
  { key: 'ports', label: 'Ports', group: 'Infrastructure', supported: true },
  { key: 'incidents', label: 'Incidents', group: 'Alerts', supported: true },
  { key: 'zones', label: 'Zones', group: 'Alerts', supported: true },
]

export default function LayerControl({ open, onClose }) {
  const activeLayers = useMapStore(s => s.activeLayers)
  const toggleLayer = useMapStore(s => s.toggleLayer)

  useEffect(() => {
    if (!open) return undefined

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  if (!open || typeof document === 'undefined') return null

  const groups = [...new Set(LAYERS.map(l => l.group))]

  return createPortal(
    <div className="fixed inset-0 z-[2100] pointer-events-none" id="layer-control">
      <button
        type="button"
        aria-label="Close layers panel"
        onClick={onClose}
        className="absolute inset-0 bg-slate-950/18 backdrop-blur-[1px] pointer-events-auto"
      />
      <div className="pointer-events-auto absolute right-4 top-24 w-[min(20rem,calc(100vw-2rem))] overflow-hidden rounded-[1.5rem] border border-cyan-400/14 bg-[rgba(10,15,28,0.98)] shadow-[0_28px_80px_rgba(2,6,23,0.72)] backdrop-blur-xl md:right-6 md:top-28">
        <div className="flex items-start justify-between border-b border-slate-800/90 px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-white">Layers</h3>
            <p className="mt-1 text-xs text-slate-400">Choose what appears on the chart.</p>
          </div>
          <button type="button" onClick={onClose} className="text-slate-500 transition hover:text-slate-300">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>
        <div className="max-h-[min(34rem,calc(100vh-8rem))] space-y-3 overflow-y-auto px-3 py-3">
          {groups.map(group => (
            <div key={group}>
              <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{group}</div>
              {LAYERS.filter(l => l.group === group).map(layer => (
                <label
                  key={layer.key}
                  className={`flex items-center gap-3 rounded-2xl border px-3 py-2.5 text-sm transition ${
                    layer.supported
                      ? 'cursor-pointer border-slate-800/90 bg-slate-950/45 text-slate-300 hover:border-cyan-400/20 hover:text-slate-100'
                      : 'cursor-not-allowed border-slate-900/90 bg-slate-950/25 text-slate-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={activeLayers[layer.key] ?? false}
                    onChange={() => layer.supported && toggleLayer(layer.key)}
                    disabled={!layer.supported}
                    className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-800"
                  />
                  <span className="flex-1">{layer.label}</span>
                  {!layer.supported && (
                    <span className="text-[10px] uppercase tracking-[0.18em] text-slate-600">Soon</span>
                  )}
                </label>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>,
    document.body,
  )
}
