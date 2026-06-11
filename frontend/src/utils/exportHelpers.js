/* Export helpers — GPX, CSV, JSON, and plain-text reports */
export function downloadContent(content, filename, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function exportRowsAsCSV(headers, rows, filename = 'export.csv') {
  const headerLine = headers.join(',')
  const rowLines = rows
    .map((row) =>
      headers
        .map((header) => {
          const value = row[header]
          const safe = value == null ? '' : String(value).replaceAll('"', '""')
          return `"${safe}"`
        })
        .join(','),
    )
    .join('\n')

  downloadContent(`${headerLine}\n${rowLines}`, filename, 'text/csv')
}

export function exportAsJSON(data, filename = 'report.json') {
  downloadContent(JSON.stringify(data, null, 2), filename, 'application/json')
}

export function exportAsText(content, filename = 'report.txt') {
  downloadContent(content, filename, 'text/plain')
}

export function exportAsCSV(points, filename = 'track.csv') {
  exportRowsAsCSV(
    ['timestamp', 'latitude', 'longitude', 'speed', 'heading', 'course'],
    points.map((point) => ({
      timestamp: point.timestamp,
      latitude: point.latitude,
      longitude: point.longitude,
      speed: point.speed || '',
      heading: point.heading || '',
      course: point.course || '',
    })),
    filename,
  )
}

export function exportAsGPX(points, vesselName = 'Vessel', filename = 'track.gpx') {
  const trkpts = points.map((point) =>
    `    <trkpt lat="${point.latitude}" lon="${point.longitude}"><time>${point.timestamp}</time><speed>${point.speed || 0}</speed></trkpt>`,
  ).join('\n')
  const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="SeaTracker">
  <trk><name>${vesselName}</name><trkseg>
${trkpts}
  </trkseg></trk>
</gpx>`
  downloadContent(gpx, filename, 'application/gpx+xml')
}
