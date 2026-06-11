/* Geospatial helper functions for the frontend */
export function haversineNM(lat1, lon1, lat2, lon2) {
  const R = 3440.065
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLon/2)**2
  return R * 2 * Math.asin(Math.sqrt(a))
}

export function getBounds(vessels) {
  if (!vessels.length) return null
  let minLat = 90, maxLat = -90, minLon = 180, maxLon = -180
  vessels.forEach(v => {
    if (v.latitude && v.longitude) {
      minLat = Math.min(minLat, v.latitude)
      maxLat = Math.max(maxLat, v.latitude)
      minLon = Math.min(minLon, v.longitude)
      maxLon = Math.max(maxLon, v.longitude)
    }
  })
  return [[minLat, minLon], [maxLat, maxLon]]
}

function getPortBucketKey(port, cellSizeDegrees) {
  const latBucket = Math.floor((port.latitude + 90) / cellSizeDegrees)
  const lngBucket = Math.floor((port.longitude + 180) / cellSizeDegrees)
  return `${latBucket}:${lngBucket}`
}

export function samplePortsForViewport(ports, limit, cellSizeDegrees = 12) {
  if (!Array.isArray(ports) || limit <= 0) return []
  if (ports.length <= limit) return ports

  const buckets = new Map()
  ports.forEach((port) => {
    const bucketKey = getPortBucketKey(port, cellSizeDegrees)
    if (!buckets.has(bucketKey)) {
      buckets.set(bucketKey, [])
    }
    buckets.get(bucketKey).push(port)
  })

  const bucketList = Array.from(buckets.values())
    .sort((left, right) => right.length - left.length)

  const sampled = []
  let offset = 0

  while (sampled.length < limit) {
    let addedInRound = false

    for (const bucket of bucketList) {
      if (offset < bucket.length) {
        sampled.push(bucket[offset])
        addedInRound = true
        if (sampled.length >= limit) {
          break
        }
      }
    }

    if (!addedInRound) {
      break
    }

    offset += 1
  }

  return sampled
}
