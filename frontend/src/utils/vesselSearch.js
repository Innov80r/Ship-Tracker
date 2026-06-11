import { getTypeName } from './aisHelpers'

const GENERIC_VESSEL_TERMS = [
  'ship',
  'ships',
  'vessel',
  'vessels',
  'boat',
  'boats',
  'sea',
  'marine',
  'maritime',
  'ocean',
]

const TYPE_KEYWORDS = {
  30: ['fishing', 'trawler', 'trawlers'],
  31: ['towing', 'tug', 'tugboat', 'tugboats'],
  32: ['towing', 'tug', 'tugboat', 'tugboats'],
  33: ['dredger', 'dredging'],
  34: ['diving', 'support vessel', 'offshore support'],
  35: ['military', 'navy', 'naval', 'warship', 'warships', 'submarine', 'submarines'],
  36: ['sailing', 'sailboat', 'sailboats', 'yacht'],
  37: ['pleasure', 'recreational', 'yacht', 'yachts'],
  40: ['high speed', 'fast craft', 'patrol craft'],
  50: ['pilot', 'pilot boat'],
  51: ['sar', 'search and rescue', 'rescue'],
  52: ['tug', 'tugboat', 'harbor tug', 'harbour tug'],
  53: ['port tender', 'harbor service', 'harbour service'],
  54: ['anti pollution', 'pollution response'],
  55: ['law enforcement', 'coast guard', 'patrol', 'police'],
  58: ['medical', 'hospital ship'],
  60: ['passenger', 'ferry', 'cruise', 'liner'],
  70: ['cargo', 'freighter', 'merchant', 'merchant ship'],
  80: ['tanker', 'oil tanker', 'chemical tanker', 'gas carrier'],
  90: ['service vessel'],
}

function keywordsForType(code) {
  if (typeof code !== 'number') return []
  if (TYPE_KEYWORDS[code]) return TYPE_KEYWORDS[code]
  return TYPE_KEYWORDS[Math.floor(code / 10) * 10] || []
}

function buildVesselSearchText(vessel) {
  const typeName = vessel.vessel_type_name || getTypeName(vessel.vessel_type)

  return [
    vessel.name,
    vessel.mmsi,
    vessel.call_sign,
    vessel.imo,
    vessel.destination,
    vessel.flag_country,
    typeName,
    ...GENERIC_VESSEL_TERMS,
    ...keywordsForType(vessel.vessel_type),
  ]
    .filter((value) => value !== null && value !== undefined && value !== '')
    .join(' ')
    .toLowerCase()
}

export function matchesVesselSearch(vessel, query) {
  const normalizedQuery = query.trim().toLowerCase()
  if (normalizedQuery.length < 2) return false
  return buildVesselSearchText(vessel).includes(normalizedQuery)
}
