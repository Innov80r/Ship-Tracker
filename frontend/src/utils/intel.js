import { formatDistanceToNowStrict } from 'date-fns'
import { getTypeName } from './aisHelpers'
import { matchesVesselSearch } from './vesselSearch'

const CATEGORY_BY_BASE = {
  30: 'fishing',
  31: 'service',
  32: 'service',
  33: 'industrial',
  34: 'industrial',
  35: 'military',
  36: 'recreational',
  37: 'recreational',
  40: 'response',
  50: 'service',
  51: 'response',
  52: 'service',
  53: 'service',
  54: 'response',
  55: 'security',
  58: 'response',
  60: 'passenger',
  70: 'cargo',
  80: 'tanker',
  90: 'other',
}

const COMMERCIAL_CATEGORIES = new Set(['cargo', 'tanker', 'passenger', 'fishing'])

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

function toNumber(value, fallback = 0) {
  return Number.isFinite(value) ? value : fallback
}

function toTimestamp(value) {
  const timestamp = value ? new Date(value).getTime() : NaN
  return Number.isFinite(timestamp) ? timestamp : null
}

export function getTypeBase(code) {
  if (typeof code !== 'number') return null
  const base = Math.floor(code / 10) * 10
  return CATEGORY_BY_BASE[code] ? code : base
}

export function getVesselCategory(vessel) {
  const base = getTypeBase(vessel?.vessel_type)
  return CATEGORY_BY_BASE[base] || 'other'
}

export function isMilitaryVessel(vessel) {
  return getVesselCategory(vessel) === 'military' || getVesselCategory(vessel) === 'security'
}

export function isCommercialVessel(vessel) {
  return COMMERCIAL_CATEGORIES.has(getVesselCategory(vessel))
}

export function getLastSeenMinutes(vessel) {
  const timestamp = toTimestamp(vessel?.last_updated)
  if (!timestamp) return Number.POSITIVE_INFINITY
  return (Date.now() - timestamp) / 60000
}

export function isDarkVessel(vessel, thresholdMinutes = 45) {
  return getLastSeenMinutes(vessel) >= thresholdMinutes
}

export function formatLastSeen(vessel) {
  const timestamp = vessel?.last_updated
  if (!timestamp) return 'No telemetry'
  try {
    return formatDistanceToNowStrict(new Date(timestamp), { addSuffix: true })
  } catch {
    return 'Unknown'
  }
}

export function getWeatherImpactScoreFromPoint(point) {
  if (!point) return 0
  const wave = toNumber(point.wave_height)
  const wind = toNumber(point.wind_speed)
  const current = toNumber(point.current_speed)
  const tide = Math.abs(toNumber(point.water_level))

  let score = 0
  score += clamp((wave / 5) * 45, 0, 45)
  score += clamp((wind / 45) * 35, 0, 35)
  score += clamp((current / 3) * 12, 0, 12)
  score += clamp((tide / 4) * 8, 0, 8)
  return Math.round(clamp(score, 0, 100))
}

export function haversineNm(lat1, lon1, lat2, lon2) {
  const toRad = (value) => value * Math.PI / 180
  const radiusNm = 3440.065
  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2
  return radiusNm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

export function getNearestWeatherPoint(vessel, weatherPoints) {
  if (!Array.isArray(weatherPoints) || weatherPoints.length === 0) return null
  if (vessel?.latitude == null || vessel?.longitude == null) return null

  let nearest = null
  let bestDistance = Number.POSITIVE_INFINITY

  weatherPoints.forEach((point) => {
    if (point.lat == null || point.lon == null) return
    const roughLat = Math.abs(point.lat - vessel.latitude)
    const roughLon = Math.abs(point.lon - vessel.longitude)
    if (roughLat > 8 || roughLon > 8) return

    const distance = haversineNm(vessel.latitude, vessel.longitude, point.lat, point.lon)
    if (distance < bestDistance) {
      bestDistance = distance
      nearest = point
    }
  })

  return nearest
}

export function getRiskAssessment(vessel, options = {}) {
  const { darkThresholdMinutes = 45, weatherPoint = null } = options
  const reasons = []
  let score = 6

  const weatherImpact = getWeatherImpactScoreFromPoint(weatherPoint)

  if (vessel?.nav_status === 14) {
    score += 65
    reasons.push('Distress beacon active')
  } else if ([2, 3, 6].includes(vessel?.nav_status)) {
    score += 20
    reasons.push('Restricted manoeuvrability')
  }

  if (toNumber(vessel?.speed) > 24) {
    score += 10
    reasons.push('High-speed transit')
  }

  if (toNumber(vessel?.speed) > 2 && !vessel?.destination) {
    score += 6
    reasons.push('No declared destination')
  }

  if (isMilitaryVessel(vessel)) {
    score += 12
    reasons.push('Military or security profile')
  }

  if (isDarkVessel(vessel, darkThresholdMinutes)) {
    score += 22
    reasons.push('AIS gap / stale telemetry')
  }

  if (toNumber(vessel?.draught) >= 12) {
    score += 6
    reasons.push('Deep-draught vessel')
  }

  if (toNumber(vessel?.length) >= 250) {
    score += 5
    reasons.push('Large hull footprint')
  }

  if (weatherImpact >= 55) {
    score += Math.round(weatherImpact * 0.35)
    reasons.push('Weather impact')
  }

  score = clamp(score, 0, 100)

  let level = 'low'
  if (score >= 78) level = 'critical'
  else if (score >= 58) level = 'high'
  else if (score >= 35) level = 'medium'

  return {
    score,
    level,
    reasons,
    weatherImpact,
  }
}

export function destinationPoint(lat, lon, bearingDegrees, distanceNm) {
  const earthRadiusNm = 3440.065
  const angularDistance = distanceNm / earthRadiusNm
  const bearing = bearingDegrees * Math.PI / 180
  const startLat = lat * Math.PI / 180
  const startLon = lon * Math.PI / 180

  const endLat = Math.asin(
    Math.sin(startLat) * Math.cos(angularDistance) +
    Math.cos(startLat) * Math.sin(angularDistance) * Math.cos(bearing),
  )

  const endLon = startLon + Math.atan2(
    Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(startLat),
    Math.cos(angularDistance) - Math.sin(startLat) * Math.sin(endLat),
  )

  return [
    endLat * 180 / Math.PI,
    ((endLon * 180 / Math.PI + 540) % 360) - 180,
  ]
}

export function getProjectedRoute(vessel, horizons = [1, 3, 6, 12]) {
  if (vessel?.latitude == null || vessel?.longitude == null) return []
  const speed = toNumber(vessel?.speed)
  const bearing = toNumber(vessel?.heading, toNumber(vessel?.course))
  if (speed <= 0.1 || !Number.isFinite(bearing)) return []

  const points = [[vessel.latitude, vessel.longitude]]
  horizons.forEach((hours) => {
    points.push(destinationPoint(vessel.latitude, vessel.longitude, bearing, speed * hours))
  })
  return points
}

export function getTransitEta(vessel, distanceNm = 120) {
  const speed = toNumber(vessel?.speed)
  if (speed <= 0.1) return null
  const hours = distanceNm / speed
  return {
    distanceNm,
    hours,
    eta: new Date(Date.now() + hours * 3600000).toISOString(),
  }
}

export function filterVessels(vessels, filters, watchlistMmsis = []) {
  const watchlistSet = new Set(watchlistMmsis)

  return vessels.filter((vessel) => {
    if (!matchesVesselSearch(vessel, filters.searchQuery || '  ') && filters.searchQuery.trim().length >= 2) {
      return false
    }

    const category = getVesselCategory(vessel)
    const risk = getRiskAssessment(vessel).score

    if (filters.vesselCategories.length && !filters.vesselCategories.includes(category)) return false
    if (filters.vesselTypes.length && !filters.vesselTypes.includes(vessel.vessel_type)) return false
    if (filters.flagCountries.length && !filters.flagCountries.includes(vessel.flag_country || 'Unknown')) return false
    if (filters.navStatuses.length && !filters.navStatuses.includes(vessel.nav_status)) return false
    if (filters.dataSources.length && !filters.dataSources.includes(vessel.data_source || 'Unknown')) return false
    if (toNumber(vessel.speed) < filters.speedRange[0] || toNumber(vessel.speed) > filters.speedRange[1]) return false
    if (toNumber(vessel.draught) < filters.draughtRange[0] || toNumber(vessel.draught) > filters.draughtRange[1]) return false
    if (toNumber(vessel.length) < filters.lengthRange[0] || toNumber(vessel.length) > filters.lengthRange[1]) return false
    if (getLastSeenMinutes(vessel) > filters.lastSeenMaxMinutes) return false
    if (risk < filters.riskMinimum) return false
    if (filters.watchlistOnly && !watchlistSet.has(vessel.mmsi)) return false
    if (filters.darkOnly && !isDarkVessel(vessel)) return false
    if (filters.weatherImpactOnly) {
      const weatherImpact = getRiskAssessment(vessel).weatherImpact
      if (weatherImpact && weatherImpact < 55) return false
    }
    if (filters.destinationRequired && !vessel.destination) return false
    return true
  })
}

export function getTrafficCorridors(vessels, granularity = 8) {
  const cells = new Map()

  vessels.forEach((vessel) => {
    if (vessel.latitude == null || vessel.longitude == null) return
    const latCell = Math.floor((vessel.latitude + 90) / granularity)
    const lonCell = Math.floor((vessel.longitude + 180) / granularity)
    const key = `${latCell}:${lonCell}`
    const current = cells.get(key) || { count: 0, avgSpeed: 0, latCell, lonCell }
    current.count += 1
    current.avgSpeed += toNumber(vessel.speed)
    cells.set(key, current)
  })

  return Array.from(cells.values())
    .map((cell) => ({
      ...cell,
      avgSpeed: cell.count ? Number((cell.avgSpeed / cell.count).toFixed(1)) : 0,
      label: `${cell.latCell * granularity - 90}°/${cell.lonCell * granularity - 180}° sector`,
    }))
    .sort((left, right) => right.count - left.count)
    .slice(0, 12)
}

export function getFleetGroups(vessels, mode = 'type') {
  const buckets = new Map()

  vessels.forEach((vessel) => {
    let key = 'Unknown'
    if (mode === 'type') key = getTypeName(vessel.vessel_type)
    if (mode === 'flag') key = vessel.flag_country || 'Unknown'
    if (mode === 'source') key = vessel.data_source || 'Unknown'
    if (mode === 'category') key = getVesselCategory(vessel)

    const current = buckets.get(key) || { key, count: 0, avgSpeed: 0, dark: 0, risky: 0 }
    current.count += 1
    current.avgSpeed += toNumber(vessel.speed)
    if (isDarkVessel(vessel)) current.dark += 1
    if (getRiskAssessment(vessel).score >= 58) current.risky += 1
    buckets.set(key, current)
  })

  return Array.from(buckets.values())
    .map((bucket) => ({
      ...bucket,
      avgSpeed: bucket.count ? Number((bucket.avgSpeed / bucket.count).toFixed(1)) : 0,
    }))
    .sort((left, right) => right.count - left.count)
}

export function getPortCongestion(ports, vessels, radiusNm = 14) {
  const portList = Array.isArray(ports) ? ports : []
  const vesselList = Array.isArray(vessels) ? vessels : []
  const ranked = []

  portList.forEach((port) => {
    if (port.latitude == null || port.longitude == null) return

    let count = 0
    let anchored = 0
    let queue = 0
    let avgSpeed = 0

    vesselList.forEach((vessel) => {
      if (vessel.latitude == null || vessel.longitude == null) return
      if (Math.abs(vessel.latitude - port.latitude) > 1.2 || Math.abs(vessel.longitude - port.longitude) > 1.2) return

      const distance = haversineNm(port.latitude, port.longitude, vessel.latitude, vessel.longitude)
      if (distance > radiusNm) return

      count += 1
      avgSpeed += toNumber(vessel.speed)
      if (vessel.nav_status === 1 || vessel.nav_status === 5) anchored += 1
      if (distance > 3 && distance <= radiusNm) queue += 1
    })

    if (!count) return

    ranked.push({
      id: port.id || port.name,
      name: port.name,
      country: port.country || 'Unknown',
      latitude: port.latitude,
      longitude: port.longitude,
      portType: port.port_type || 'port',
      vesselCount: count,
      queueCount: queue,
      anchoredCount: anchored,
      avgSpeed: Number((avgSpeed / count).toFixed(1)),
      congestionScore: Math.round(count * 3 + queue * 4 + anchored * 2),
    })
  })

  return ranked.sort((left, right) => right.congestionScore - left.congestionScore)
}

export function getOperatorReport(vessels, ports, watchlistMmsis = []) {
  const watchlistSet = new Set(watchlistMmsis)
  const riskLeaderboard = [...vessels]
    .map((vessel) => ({
      mmsi: vessel.mmsi,
      name: vessel.name || `MMSI ${vessel.mmsi}`,
      type: getTypeName(vessel.vessel_type),
      risk: getRiskAssessment(vessel).score,
      dark: isDarkVessel(vessel),
      watchlisted: watchlistSet.has(vessel.mmsi),
    }))
    .sort((left, right) => right.risk - left.risk)
    .slice(0, 10)

  return {
    generatedAt: new Date().toISOString(),
    fleetCount: vessels.length,
    darkVessels: vessels.filter((vessel) => isDarkVessel(vessel)).length,
    militaryVessels: vessels.filter((vessel) => isMilitaryVessel(vessel)).length,
    watchlistCount: vessels.filter((vessel) => watchlistSet.has(vessel.mmsi)).length,
    congestionHotspots: getPortCongestion(ports, vessels).slice(0, 10),
    riskLeaderboard,
    corridors: getTrafficCorridors(vessels),
  }
}
