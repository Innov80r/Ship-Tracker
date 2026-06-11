import { format, formatDistanceToNow } from 'date-fns'

export function formatSpeed(knots) {
  if (knots == null) return '—'
  return `${knots.toFixed(1)} kn`
}

export function formatHeading(deg) {
  if (deg == null) return '—'
  return `${Math.round(deg)}°`
}

export function formatCoord(lat, lon) {
  if (lat == null || lon == null) return '—'
  const latDir = lat >= 0 ? 'N' : 'S'
  const lonDir = lon >= 0 ? 'E' : 'W'
  return `${Math.abs(lat).toFixed(5)}° ${latDir}, ${Math.abs(lon).toFixed(5)}° ${lonDir}`
}

export function formatTimestamp(ts) {
  if (!ts) return '—'
  try {
    const d = new Date(ts)
    return format(d, 'HH:mm:ss dd MMM yyyy')
  } catch { return ts }
}

export function formatTimeAgo(ts) {
  if (!ts) return '—'
  try {
    return formatDistanceToNow(new Date(ts), { addSuffix: true })
  } catch { return ts }
}

export function formatDuration(hours) {
  if (hours == null) return '—'
  if (hours < 1) return `${Math.round(hours * 60)}m`
  if (hours < 24) return `${hours.toFixed(1)}h`
  return `${(hours / 24).toFixed(1)}d`
}

export function formatNumber(n) {
  if (n == null) return '—'
  return n.toLocaleString()
}
