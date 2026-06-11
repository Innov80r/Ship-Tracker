function normalizeText(value) {
  return String(value || '').trim().toLowerCase()
}

function createBBoxFromPoint(lat, lng) {
  if (lat == null || lng == null) return null
  return { minLng: lng, minLat: lat, maxLng: lng, maxLat: lat }
}

function getCountryName(properties = {}) {
  const territory = String(properties.territory1 || '').trim()
  const sovereign = String(properties.sovereign1 || '').trim()
  if (territory && sovereign && normalizeText(territory) !== normalizeText(sovereign)) {
    return territory
  }
  return territory || sovereign || String(properties.geoname || '').trim() || 'Unknown'
}

function getSovereignName(properties = {}) {
  return String(properties.sovereign1 || '').trim() || getCountryName(properties)
}

function appendCoordinates(node, points) {
  if (!Array.isArray(node)) return
  if (typeof node[0] === 'number' && typeof node[1] === 'number') {
    points.push([node[0], node[1]])
    return
  }
  node.forEach((child) => appendCoordinates(child, points))
}

function computeBBox(points) {
  if (!points.length) {
    return null
  }

  let minLng = Number.POSITIVE_INFINITY
  let minLat = Number.POSITIVE_INFINITY
  let maxLng = Number.NEGATIVE_INFINITY
  let maxLat = Number.NEGATIVE_INFINITY

  points.forEach(([lng, lat]) => {
    minLng = Math.min(minLng, lng)
    minLat = Math.min(minLat, lat)
    maxLng = Math.max(maxLng, lng)
    maxLat = Math.max(maxLat, lat)
  })

  return { minLng, minLat, maxLng, maxLat }
}

function mergeBBox(a, b) {
  if (!a) return b
  if (!b) return a
  return {
    minLng: Math.min(a.minLng, b.minLng),
    minLat: Math.min(a.minLat, b.minLat),
    maxLng: Math.max(a.maxLng, b.maxLng),
    maxLat: Math.max(a.maxLat, b.maxLat),
  }
}

function getZoomFromBBox(bbox) {
  if (!bbox) return 4
  const lngSpan = Math.abs(bbox.maxLng - bbox.minLng)
  const latSpan = Math.abs(bbox.maxLat - bbox.minLat)
  const span = Math.max(lngSpan, latSpan)
  if (span > 120) return 2
  if (span > 70) return 3
  if (span > 35) return 4
  if (span > 18) return 5
  if (span > 9) return 6
  if (span > 4) return 7
  return 8
}

function pointInRing(pointLng, pointLat, ring = []) {
  let inside = false
  for (let index = 0, prev = ring.length - 1; index < ring.length; prev = index, index += 1) {
    const [lng1, lat1] = ring[index]
    const [lng2, lat2] = ring[prev]
    const intersects = ((lat1 > pointLat) !== (lat2 > pointLat))
      && (pointLng < ((lng2 - lng1) * (pointLat - lat1)) / ((lat2 - lat1) || Number.EPSILON) + lng1)
    if (intersects) {
      inside = !inside
    }
  }
  return inside
}

function pointInPolygon(pointLng, pointLat, polygon = []) {
  if (!polygon.length) return false
  if (!pointInRing(pointLng, pointLat, polygon[0])) return false
  for (let index = 1; index < polygon.length; index += 1) {
    if (pointInRing(pointLng, pointLat, polygon[index])) {
      return false
    }
  }
  return true
}

function pointInGeometry(pointLng, pointLat, geometry) {
  if (!geometry) return false
  if (geometry.type === 'Polygon') {
    return pointInPolygon(pointLng, pointLat, geometry.coordinates)
  }
  if (geometry.type === 'MultiPolygon') {
    return geometry.coordinates.some((polygon) => pointInPolygon(pointLng, pointLat, polygon))
  }
  return false
}

function matchNameAgainstCountry(country, value) {
  const normalizedValue = normalizeText(value)
  return country.aliases.some((alias) => alias.includes(normalizedValue))
}

function getCenterFromBBox(bbox) {
  if (!bbox) return null
  return [
    (bbox.minLat + bbox.maxLat) / 2,
    (bbox.minLng + bbox.maxLng) / 2,
  ]
}

function ensureCountry(countries, countryName, options = {}) {
  const normalizedName = normalizeText(countryName)
  if (!normalizedName || normalizedName === 'unknown') return null

  if (!countries.has(normalizedName)) {
    countries.set(normalizedName, {
      key: normalizedName,
      name: countryName,
      sovereign: options.sovereign || countryName,
      aliases: [],
      center: null,
      bbox: null,
      features: [],
    })
  }

  const country = countries.get(normalizedName)
  country.aliases = Array.from(new Set([
    ...country.aliases,
    normalizedName,
    normalizeText(options.sovereign),
    ...(options.aliases || []).map(normalizeText),
  ].filter(Boolean)))

  if (options.feature) {
    country.features.push(options.feature)
  }

  if (options.bbox) {
    country.bbox = mergeBBox(country.bbox, options.bbox)
  }

  if (!country.center && options.center) {
    country.center = options.center
  }

  if (!country.center && country.bbox) {
    country.center = getCenterFromBBox(country.bbox)
  }

  return country
}

export function buildCountryDirectory(geojson, options = {}) {
  const features = geojson?.features || []
  const {
    catalogCountries = [],
    ports = [],
    vessels = [],
  } = options
  const countries = new Map()

  features.forEach((feature) => {
    const properties = feature?.properties || {}
    const countryName = getCountryName(properties)
    const sovereignName = getSovereignName(properties)
    if (!normalizeText(countryName) || normalizeText(countryName) === 'unknown') return

    const points = []
    appendCoordinates(feature?.geometry?.coordinates, points)
    const bbox = computeBBox(points)
    const centroid = [
      Number.isFinite(Number(properties.y_1)) ? Number(properties.y_1) : ((bbox?.minLat ?? 0) + (bbox?.maxLat ?? 0)) / 2,
      Number.isFinite(Number(properties.x_1)) ? Number(properties.x_1) : ((bbox?.minLng ?? 0) + (bbox?.maxLng ?? 0)) / 2,
    ]

    ensureCountry(countries, countryName, {
      sovereign: sovereignName,
      aliases: [properties.geoname],
      center: centroid,
      bbox,
      feature,
    })
  })

  catalogCountries.forEach((country) => {
    ensureCountry(countries, country?.name, {
      aliases: country?.aliases || [],
    })
  })

  ports.forEach((port) => {
    if (port?.country == null) return
    ensureCountry(countries, port.country, {
      bbox: createBBoxFromPoint(port.latitude, port.longitude),
      center: (port.latitude != null && port.longitude != null) ? [port.latitude, port.longitude] : null,
    })
  })

  vessels.forEach((vessel) => {
    if (!vessel?.flag_country) return
    ensureCountry(countries, vessel.flag_country, {
      bbox: createBBoxFromPoint(vessel.latitude, vessel.longitude),
      center: (vessel.latitude != null && vessel.longitude != null) ? [vessel.latitude, vessel.longitude] : null,
    })
  })

  return Array.from(countries.values())
    .map((country) => ({
      ...country,
      center: country.center || [20, 0],
      zoom: getZoomFromBBox(country.bbox),
      hasGeometry: country.features.length > 0,
    }))
    .sort((left, right) => left.name.localeCompare(right.name))
}

export function findCountryMatch(countries, query) {
  const normalizedQuery = normalizeText(query)
  if (!normalizedQuery) return null

  const exact = countries.find((country) => country.aliases.includes(normalizedQuery))
  if (exact) return exact
  return countries.find((country) => matchNameAgainstCountry(country, normalizedQuery)) || null
}

export function isPointInCountry(lat, lng, country) {
  if (!country || lat == null || lng == null) return false
  const bbox = country.bbox
  if (bbox) {
    if (lng < bbox.minLng || lng > bbox.maxLng || lat < bbox.minLat || lat > bbox.maxLat) {
      return false
    }
  }
  return country.features.some((feature) => pointInGeometry(lng, lat, feature.geometry))
}

export function filterPortsByCountry(ports, country) {
  if (!country) return ports
  return ports.filter((port) => {
    const portCountry = normalizeText(port.country)
    if (portCountry && matchNameAgainstCountry(country, portCountry)) {
      return true
    }
    return isPointInCountry(port.latitude, port.longitude, country)
  })
}

export function filterVesselsByCountry(vessels, country) {
  if (!country) return vessels
  if (country.hasGeometry) {
    return vessels.filter((vessel) => isPointInCountry(vessel.latitude, vessel.longitude, country))
  }
  return vessels.filter((vessel) => {
    const flagCountry = normalizeText(vessel.flag_country)
    return flagCountry && matchNameAgainstCountry(country, flagCountry)
  })
}

export function getFlaggedVesselsByCountry(vessels, country) {
  if (!country) return []
  return vessels.filter((vessel) => {
    const flagCountry = normalizeText(vessel.flag_country)
    return flagCountry && matchNameAgainstCountry(country, flagCountry)
  })
}
