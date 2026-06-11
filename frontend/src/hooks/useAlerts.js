import { useEffect } from 'react'
import axios from 'axios'
import useAlertStore from '../store/alertStore'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function useAlerts(enabled = true) {
  const { alerts, unreadCount, setAlerts, setUnreadCount, markRead, markAllRead } = useAlertStore()

  useEffect(() => {
    if (!enabled) return

    const load = async () => {
      try {
        const { data } = await axios.get(`${API}/api/alerts?limit=50`)
        if (data.alerts) setAlerts(data.alerts)
        const countResp = await axios.get(`${API}/api/alerts/count`)
        setUnreadCount(countResp.data.unread_count || 0)
      } catch (e) { console.warn('Alerts API error:', e.message) }
    }
    load()
  }, [enabled, setAlerts, setUnreadCount])

  const markAsRead = async (id) => {
    try {
      await axios.put(`${API}/api/alerts/${id}/read`)
      markRead(id)
    } catch {}
  }

  const markAllAsRead = async () => {
    try {
      await axios.put(`${API}/api/alerts/read-all`)
      markAllRead()
    } catch {}
  }

  return { alerts, unreadCount, markAsRead, markAllAsRead }
}
