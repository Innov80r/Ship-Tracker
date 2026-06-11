import { useEffect, useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function useCountryCatalog(enabled = true) {
  const [countries, setCountries] = useState([])

  useEffect(() => {
    if (!enabled) return

    let ignore = false
    const controller = new AbortController()

    const load = async () => {
      try {
        const response = await axios.get(`${API}/api/layers/countries`, { signal: controller.signal })
        if (!ignore) setCountries(response.data?.countries || [])
      } catch (error) {
        if (!ignore && error.code !== 'ERR_CANCELED') setCountries([])
      }
    }

    load()

    return () => {
      ignore = true
      controller.abort()
    }
  }, [enabled])

  return countries
}
