import { useEffect, useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function useLayerGeoJson(path, enabled = true) {
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!enabled || !path) return

    let ignore = false
    const controller = new AbortController()

    const load = async () => {
      try {
        const response = await axios.get(`${API}${path}`, { signal: controller.signal })
        if (!ignore) setData(response.data)
      } catch (error) {
        if (!ignore && error.code !== 'ERR_CANCELED') setData(null)
      }
    }

    load()

    return () => {
      ignore = true
      controller.abort()
    }
  }, [enabled, path])

  return data
}
