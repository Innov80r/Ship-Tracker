import { useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function useZones(enabled = true) {
  const [zones, setZones] = useState([])

  const loadZones = async () => {
    try {
      const { data } = await axios.get(`${API}/api/zones`)
      setZones(data.zones || [])
    } catch {}
  }

  useEffect(() => {
    if (!enabled) return
    loadZones()
  }, [enabled])

  const createZone = async (zoneData) => {
    try {
      await axios.post(`${API}/api/zones`, zoneData)
      await loadZones()
    } catch {}
  }

  const deleteZone = async (id) => {
    try {
      await axios.delete(`${API}/api/zones/${id}`)
      await loadZones()
    } catch {}
  }

  return { zones, createZone, deleteZone, loadZones }
}
