/* Vessel type → color mapping for markers and charts */
const VESSEL_COLORS = {
  cargo: '#3b82f6',
  tanker: '#f97316',
  passenger: '#14b8a6',
  fishing: '#eab308',
  military: '#ef4444',
  tug: '#92400e',
  sailing: '#93c5fd',
  pleasure: '#ec4899',
  high_speed: '#06b6d4',
  pilot: '#a16207',
  sar: '#dc2626',
  anti_pollution: '#115e59',
  dredger: '#78716c',
  diving_support: '#7c3aed',
  law_enforcement: '#1d4ed8',
  port_tender: '#ca8a04',
  medical: '#f43f5e',
  other: '#6b7280',
}

const TYPE_CODE_COLORS = {
  30: '#eab308', 31: '#92400e', 32: '#92400e', 33: '#78716c',
  34: '#7c3aed', 35: '#ef4444', 36: '#93c5fd', 37: '#ec4899',
  40: '#06b6d4', 50: '#a16207', 51: '#dc2626', 52: '#92400e',
  53: '#ca8a04', 54: '#115e59', 55: '#1d4ed8', 58: '#f43f5e',
  60: '#14b8a6', 61: '#14b8a6', 62: '#14b8a6', 63: '#14b8a6',
  64: '#14b8a6', 69: '#14b8a6',
  70: '#3b82f6', 71: '#3b82f6', 72: '#3b82f6', 73: '#3b82f6',
  74: '#3b82f6', 79: '#3b82f6',
  80: '#f97316', 81: '#f97316', 82: '#f97316', 83: '#f97316',
  84: '#f97316', 89: '#f97316',
  90: '#6b7280',
}

export function getVesselColor(vesselType) {
  return TYPE_CODE_COLORS[vesselType] || '#6b7280'
}

export function getCategoryColor(category) {
  return VESSEL_COLORS[category] || '#6b7280'
}

export function getStatusColor(navStatus) {
  switch (navStatus) {
    case 0: case 8: return '#22c55e' // underway
    case 1: return '#eab308' // anchored
    case 5: return '#6b7280' // moored
    case 14: return '#ef4444' // distress
    default: return '#94a3b8'
  }
}

export default VESSEL_COLORS
