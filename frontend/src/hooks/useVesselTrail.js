import { useEffect, useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function useVesselTrail(mmsi, enabled = true, minutes = 180) {
  const [trail, setTrail] = useState([])

  useEffect(() => {
    if (!enabled || !mmsi) {
      setTrail([])
      return
    }

    let ignore = false
    const controller = new AbortController()

    const loadTrail = async () => {
      try {
        const { data } = await axios.get(`${API}/api/history/${mmsi}/trail?minutes=${minutes}`, {
          signal: controller.signal,
        })
        if (!ignore) setTrail(data.trail || [])
      } catch (error) {
        if (!ignore && error.code !== 'ERR_CANCELED') setTrail([])
      }
    }

    loadTrail()
    const intervalId = setInterval(loadTrail, 60000)

    return () => {
      ignore = true
      controller.abort()
      clearInterval(intervalId)
    }
  }, [enabled, minutes, mmsi])

  return trail
}
