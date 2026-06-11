import { useEffect, useState } from 'react'
import { getApi } from '../utils/api'

const EMPTY_HEALTH = {
  status: 'unknown',
  active_sources: [],
}

const EMPTY_COVERAGE = {
  active_vessels: 0,
  unique_flag_countries: 0,
  unknown_flag_count: 0,
  active_source_count: 0,
  top_source_share: 0,
  source_breakdown: [],
  warnings: [],
}

export default function useCoverageDiagnostics(enabled = true) {
  const [health, setHealth] = useState(EMPTY_HEALTH)
  const [coverage, setCoverage] = useState(EMPTY_COVERAGE)

  useEffect(() => {
    if (!enabled) return undefined

    let cancelled = false

    const load = async () => {
      const [healthResult, coverageResult] = await Promise.allSettled([
        getApi('/api/health'),
        getApi('/api/analytics/coverage'),
      ])

      if (cancelled) return

      setHealth(healthResult.status === 'fulfilled' ? healthResult.value : EMPTY_HEALTH)
      setCoverage(coverageResult.status === 'fulfilled' ? coverageResult.value : EMPTY_COVERAGE)
    }

    load()
    const intervalId = window.setInterval(load, 60000)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [enabled])

  return { health, coverage }
}
