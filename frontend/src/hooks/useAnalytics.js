import { useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function useAnalytics() {
  const [dashboard, setDashboard] = useState({})
  const [types, setTypes] = useState([])
  const [flags, setFlags] = useState([])
  const [sources, setSources] = useState([])
  const [fastest, setFastest] = useState([])

  useEffect(() => {
    const load = async () => {
      try {
        const [d, t, f, s, fa] = await Promise.all([
          axios.get(`${API}/api/analytics/dashboard`),
          axios.get(`${API}/api/analytics/types`),
          axios.get(`${API}/api/analytics/flags`),
          axios.get(`${API}/api/analytics/sources`),
          axios.get(`${API}/api/analytics/fastest`),
        ])
        setDashboard(d.data || {})
        setTypes(t.data.types || [])
        setFlags(f.data.flags || [])
        setSources(s.data.sources || [])
        setFastest(fa.data.fastest || [])
      } catch {}
    }
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [])

  return { dashboard, types, flags, sources, fastest }
}
