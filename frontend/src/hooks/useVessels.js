import { useEffect } from 'react'
import axios from 'axios'
import useVesselStore from '../store/vesselStore'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const VESSEL_REFRESH_INTERVAL_MS = 60000
const LIVE_WINDOW_MINUTES = Number(import.meta.env.VITE_LIVE_WINDOW_MINUTES || 5)

export default function useVessels() {
  const { vessels, vesselCount, selectedVessel, selectVessel, clearSelection, updateVessels, removeStale } = useVesselStore()

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const { data } = await axios.get(`${API}/api/vessels`, {
          params: { last_seen_minutes: LIVE_WINDOW_MINUTES },
        })
        if (!cancelled && data.vessels) updateVessels(data.vessels)
      } catch (e) { console.warn('Vessels API error:', e.message) }
    }

    load()
    const refreshInterval = setInterval(load, VESSEL_REFRESH_INTERVAL_MS)
    const staleInterval = setInterval(() => removeStale(LIVE_WINDOW_MINUTES * 60 * 1000), 60000)

    return () => {
      cancelled = true
      clearInterval(refreshInterval)
      clearInterval(staleInterval)
    }
  }, [])

  const searchVessels = async (query) => {
    try {
      const { data } = await axios.get(`${API}/api/vessels/search?q=${encodeURIComponent(query)}`)
      return data.results || []
    } catch { return [] }
  }

  const getVessel = async (mmsi) => {
    try {
      const { data } = await axios.get(`${API}/api/vessels/${mmsi}`)
      return data
    } catch { return null }
  }

  return { vessels: Object.values(vessels), vesselCount, selectedVessel, selectVessel, clearSelection, searchVessels, getVessel }
}
