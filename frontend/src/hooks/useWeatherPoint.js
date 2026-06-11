import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function useWeatherPoint(lat, lon, enabled = true) {
  const [conditions, setConditions] = useState(null)
  const [loading, setLoading] = useState(false)

  const positionKey = useMemo(() => {
    if (lat == null || lon == null) return null
    return `${lat.toFixed(2)}:${lon.toFixed(2)}`
  }, [lat, lon])

  useEffect(() => {
    if (!enabled || !positionKey) {
      setConditions(null)
      setLoading(false)
      return
    }

    let ignore = false
    const controller = new AbortController()

    const loadConditions = async () => {
      setLoading(true)
      try {
        const { data } = await axios.get(`${API}/api/weather/point?lat=${lat}&lon=${lon}`, {
          signal: controller.signal,
        })
        if (!ignore) setConditions(data)
      } catch (error) {
        if (!ignore && error.code !== 'ERR_CANCELED') setConditions(null)
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    loadConditions()

    return () => {
      ignore = true
      controller.abort()
    }
  }, [enabled, lat, lon, positionKey])

  return { conditions, loading }
}
