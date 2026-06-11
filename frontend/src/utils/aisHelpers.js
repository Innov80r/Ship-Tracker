/* AIS type/status code lookups for the frontend */
export const VESSEL_TYPES = {
  30: 'Fishing', 31: 'Towing', 32: 'Towing (large)', 33: 'Dredger',
  34: 'Diving support', 35: 'Military', 36: 'Sailing', 37: 'Pleasure craft',
  40: 'High speed craft', 50: 'Pilot', 51: 'SAR', 52: 'Tug', 53: 'Port tender',
  54: 'Anti-pollution', 55: 'Law enforcement', 58: 'Medical',
  60: 'Passenger', 70: 'Cargo', 80: 'Tanker', 90: 'Other',
}

export const NAV_STATUSES = {
  0: 'Under way', 1: 'At anchor', 2: 'Not under command',
  3: 'Restricted manoeuvrability', 4: 'Constrained by draught',
  5: 'Moored', 6: 'Aground', 7: 'Fishing', 8: 'Sailing',
  14: 'AIS-SART (Distress)', 15: 'Not defined',
}

export function getTypeName(code) {
  if (!code) return 'Unknown'
  // Check exact
  if (VESSEL_TYPES[code]) return VESSEL_TYPES[code]
  // Check range
  const base = Math.floor(code / 10) * 10
  return VESSEL_TYPES[base] || `Type ${code}`
}

export function getNavStatus(code) {
  return NAV_STATUSES[code] || 'Unknown'
}
