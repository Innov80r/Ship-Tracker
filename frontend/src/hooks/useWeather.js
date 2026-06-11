import { useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function useWeather(enabled = true) {
  const [weather, setWeather] = useState([])
  const [tides, setTides] = useState([])

  useEffect(() => {
    if (!enabled) {
      setWeather([])
      setTides([])
      return
    }

    const load = async () => {
      try {
        const [wRes, tRes] = await Promise.all([
          axios.get(`${API}/api/weather/grid`),
          axios.get(`${API}/api/weather/tides`),
        ])
        setWeather(wRes.data.weather || [])
        setTides(tRes.data.tides || [])
      } catch {}
    }
    load()
    const interval = setInterval(load, 900000)
    return () => clearInterval(interval)
  }, [enabled])

  return { weather, tides }
}
