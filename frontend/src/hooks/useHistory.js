import { useState } from 'react'
import { getApi } from '../utils/api'

export default function useHistory() {
  const [track, setTrack] = useState([])
  const [events, setEvents] = useState([])
  const [routePrediction, setRoutePrediction] = useState(null)
  const [loading, setLoading] = useState(false)

  const loadHistory = async (mmsi, start, end) => {
    setLoading(true)
    try {
      const params = {}
      if (start) params.start = start
      if (end) params.end = end

      const [historyResult, eventsResult, routeResult] = await Promise.allSettled([
        getApi(`/api/history/${mmsi}`, { params }),
        getApi(`/api/history/${mmsi}/events`, { params }),
        getApi(`/api/intel/route/${mmsi}`),
      ])

      setTrack(historyResult.status === 'fulfilled' ? historyResult.value.points || [] : [])
      setEvents(eventsResult.status === 'fulfilled' ? eventsResult.value.events || [] : [])
      setRoutePrediction(
        routeResult.status === 'fulfilled' && !routeResult.value?.error
          ? routeResult.value
          : null,
      )
    } catch {
      setTrack([])
      setEvents([])
      setRoutePrediction(null)
    }
    setLoading(false)
  }

  const loadTrail = async (mmsi, minutes = 30) => {
    try {
      const data = await getApi(`/api/history/${mmsi}/trail`, { params: { minutes } })
      return data.trail || []
    } catch { return [] }
  }

  return { track, events, routePrediction, loading, loadHistory, loadTrail }
}
