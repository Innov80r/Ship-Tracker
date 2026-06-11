import { useEffect } from 'react'
import axios from 'axios'
import useIncidentStore from '../store/incidentStore'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function useIncidents(enabled = true) {
  const { incidents, activeCount, hasMayday, setIncidents, resolveIncident } = useIncidentStore()

  useEffect(() => {
    if (!enabled) return

    const load = async () => {
      try {
        const { data } = await axios.get(`${API}/api/incidents`)
        if (data.incidents) setIncidents(data.incidents)
      } catch (e) { console.warn('Incidents API error:', e.message) }
    }
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [enabled, setIncidents])

  const resolve = async (id) => {
    try {
      await axios.put(`${API}/api/incidents/${id}/resolve`)
      resolveIncident(id)
    } catch {}
  }

  return { incidents, activeCount, hasMayday, resolve }
}
