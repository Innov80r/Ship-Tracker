import L from 'leaflet'
import { getVesselColor, getStatusColor } from './vesselColors'

/**
 * Creates an SVG vessel icon as a Leaflet DivIcon.
 * Ship shape rotated to true heading, colored by vessel type, with status ring.
 */
export function createVesselIcon(vessel) {
  const color = getVesselColor(vessel.vessel_type)
  const statusColor = getStatusColor(vessel.nav_status)
  const heading = vessel.heading || vessel.course || 0
  const isDistress = vessel.nav_status === 14
  const size = 24

  const svg = `
    <svg width="${size}" height="${size}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="11" fill="none" stroke="${statusColor}" stroke-width="2" opacity="0.6"/>
      <g transform="rotate(${heading}, 12, 12)">
        <path d="M12 2 L18 20 L12 16 L6 20 Z" fill="${color}" stroke="#fff" stroke-width="0.8" opacity="0.95"/>
      </g>
    </svg>
  `

  return L.divIcon({
    html: `<div class="vessel-marker ${isDistress ? 'vessel-distress' : ''}" style="width:${size}px;height:${size}px;">${svg}</div>`,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  })
}

/**
 * Creates a port marker icon.
 */
export function createPortIcon() {
  return L.divIcon({
    html: `<div style="width:12px;height:12px;background:#00c9a7;border:2px solid #0f1f3c;border-radius:50%;box-shadow:0 0 6px rgba(0,201,167,0.5);"></div>`,
    className: '',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  })
}

/**
 * Creates a distress incident marker — large pulsing red.
 */
export function createIncidentIcon() {
  return L.divIcon({
    html: `<div class="vessel-distress" style="width:32px;height:32px;display:flex;align-items:center;justify-content:center;">
      <svg width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="14" fill="#ff4757" stroke="#fff" stroke-width="2"/><text x="16" y="21" text-anchor="middle" fill="#fff" font-size="14" font-weight="bold">!</text></svg>
    </div>`,
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  })
}

export default createVesselIcon
