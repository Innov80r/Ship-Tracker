import { useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function usePorts(enabled = true) {
  const [ports, setPorts] = useState([])

  useEffect(() => {
    if (!enabled) return

    const load = async () => {
      try {
        const { data } = await axios.get(`${API}/api/ports`)
        setPorts(data.ports || [])
      } catch {}
    }
    load()
  }, [enabled])

  const searchPorts = async (q) => {
    try {
      const { data } = await axios.get(`${API}/api/ports/search?q=${encodeURIComponent(q)}`)
      return data.results || []
    } catch { return [] }
  }

  return { ports, searchPorts }
}
