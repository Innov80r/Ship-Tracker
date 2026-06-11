import { useEffect, useRef, useCallback } from 'react'
import useVesselStore from '../store/vesselStore'
import useAlertStore from '../store/alertStore'
import useIncidentStore from '../store/incidentStore'
import useIntelStore from '../store/intelStore'
import { toast } from 'react-toastify'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export default function useWebSocket() {
  const vesselWs = useRef(null)
  const alertWs = useRef(null)
  const incidentWs = useRef(null)
  const connectTimer = useRef(null)
  const vesselReconnectTimer = useRef(null)
  const alertReconnectTimer = useRef(null)
  const incidentReconnectTimer = useRef(null)
  const manualCloseRef = useRef(false)
  const vesselBuffer = useRef(new Map())
  const vesselFlushTimer = useRef(null)
  const updateVesselBatch = useVesselStore(s => s.updateVesselBatch)
  const addAlert = useAlertStore(s => s.addAlert)
  const addIncident = useIncidentStore(s => s.addIncident)
  const browserNotificationsEnabled = useIntelStore((state) => state.browserNotificationsEnabled)
  const notificationRules = useIntelStore((state) => state.notificationRules)

  const shouldSendBrowserNotification = useCallback((payload, kind) => {
    if (!browserNotificationsEnabled) return false
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return false

    const alertType = String(payload?.alert_type || payload?.incident_type || '').toLowerCase()
    const severity = String(payload?.severity || '').toLowerCase()

    return notificationRules.some((rule) => {
      if (!rule.enabled || rule.channel !== 'browser') return false
      if (rule.severity && rule.severity !== severity && severity) return false
      if (rule.event === 'distress') {
        return kind === 'incident' || alertType.includes('mayday') || alertType.includes('distress') || alertType.includes('sart')
      }
      if (rule.event === 'military') {
        return alertType.includes('military')
      }
      if (rule.event === 'dark-vessel') {
        return alertType.includes('dark')
      }
      return true
    })
  }, [browserNotificationsEnabled, notificationRules])

  const flushVesselBuffer = useCallback(() => {
    vesselFlushTimer.current = null
    if (vesselBuffer.current.size === 0) return
    updateVesselBatch(Array.from(vesselBuffer.current.values()))
    vesselBuffer.current.clear()
  }, [updateVesselBatch])

  const scheduleVesselFlush = useCallback(() => {
    if (vesselFlushTimer.current) return
    vesselFlushTimer.current = setTimeout(flushVesselBuffer, 100)
  }, [flushVesselBuffer])

  const clearReconnectTimer = useCallback((timerRef) => {
    if (!timerRef.current) return
    clearTimeout(timerRef.current)
    timerRef.current = null
  }, [])

  const closeSocket = useCallback((socketRef) => {
    const socket = socketRef.current
    if (!socket) return

    socket.onopen = null
    socket.onmessage = null
    socket.onerror = null
    socket.onclose = null

    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close()
    }

    socketRef.current = null
  }, [])

  const connectVessels = useCallback(() => {
    if (manualCloseRef.current) return
    if (
      vesselWs.current?.readyState === WebSocket.OPEN ||
      vesselWs.current?.readyState === WebSocket.CONNECTING
    ) return

    const ws = new WebSocket(`${WS_URL}/ws/vessels`)
    ws.onopen = () => console.log('🟢 Vessel WS connected')
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'vessel_update' && msg.data?.mmsi != null) {
          vesselBuffer.current.set(msg.data.mmsi, msg.data)
          scheduleVesselFlush()
        }
      } catch {}
    }
    ws.onclose = () => {
      vesselWs.current = null
      if (manualCloseRef.current || vesselReconnectTimer.current) return
      vesselReconnectTimer.current = setTimeout(() => {
        vesselReconnectTimer.current = null
        connectVessels()
      }, 3000)
    }
    ws.onerror = () => {
      if (!manualCloseRef.current) ws.close()
    }
    vesselWs.current = ws
  }, [scheduleVesselFlush])

  const connectAlerts = useCallback(() => {
    if (manualCloseRef.current) return
    if (
      alertWs.current?.readyState === WebSocket.OPEN ||
      alertWs.current?.readyState === WebSocket.CONNECTING
    ) return

    const ws = new WebSocket(`${WS_URL}/ws/alerts`)
    ws.onopen = () => console.log('🟢 Alert WS connected')
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'alert' && msg.data) {
          addAlert(msg.data)
          const sev = msg.data.severity
          const toastFn = sev === 'critical' ? toast.error : sev === 'warning' ? toast.warn : toast.info
          toastFn(msg.data.title, { icon: sev === 'critical' ? '🚨' : '⚠️' })
          if (shouldSendBrowserNotification(msg.data, 'alert')) {
            new Notification(msg.data.title || 'Sea Tracker alert', {
              body: msg.data.message || msg.data.alert_type || 'New alert',
            })
          }
        }
      } catch {}
    }
    ws.onclose = () => {
      alertWs.current = null
      if (manualCloseRef.current || alertReconnectTimer.current) return
      alertReconnectTimer.current = setTimeout(() => {
        alertReconnectTimer.current = null
        connectAlerts()
      }, 3000)
    }
    ws.onerror = () => {
      if (!manualCloseRef.current) ws.close()
    }
    alertWs.current = ws
  }, [addAlert, shouldSendBrowserNotification])

  const connectIncidents = useCallback(() => {
    if (manualCloseRef.current) return
    if (
      incidentWs.current?.readyState === WebSocket.OPEN ||
      incidentWs.current?.readyState === WebSocket.CONNECTING
    ) return

    const ws = new WebSocket(`${WS_URL}/ws/incidents`)
    ws.onopen = () => console.log('🟢 Incident WS connected')
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'incident' && msg.data) {
          addIncident(msg.data)
          toast.error(`🆘 ${msg.data.incident_type}: ${msg.data.vessel_name || 'Unknown vessel'}`)
          if (shouldSendBrowserNotification(msg.data, 'incident')) {
            new Notification(`Incident: ${msg.data.incident_type}`, {
              body: msg.data.vessel_name || `MMSI ${msg.data.mmsi || 'unknown'}`,
            })
          }
        }
      } catch {}
    }
    ws.onclose = () => {
      incidentWs.current = null
      if (manualCloseRef.current || incidentReconnectTimer.current) return
      incidentReconnectTimer.current = setTimeout(() => {
        incidentReconnectTimer.current = null
        connectIncidents()
      }, 3000)
    }
    ws.onerror = () => {
      if (!manualCloseRef.current) ws.close()
    }
    incidentWs.current = ws
  }, [addIncident, shouldSendBrowserNotification])

  useEffect(() => {
    manualCloseRef.current = false
    connectTimer.current = setTimeout(() => {
      connectTimer.current = null
      connectVessels()
      connectAlerts()
      connectIncidents()
    }, 0)

    return () => {
      manualCloseRef.current = true
      if (connectTimer.current) clearTimeout(connectTimer.current)
      clearReconnectTimer(vesselReconnectTimer)
      clearReconnectTimer(alertReconnectTimer)
      clearReconnectTimer(incidentReconnectTimer)
      if (vesselFlushTimer.current) clearTimeout(vesselFlushTimer.current)
      flushVesselBuffer()
      closeSocket(vesselWs)
      closeSocket(alertWs)
      closeSocket(incidentWs)
    }
  }, [clearReconnectTimer, closeSocket, connectAlerts, connectIncidents, connectVessels, flushVesselBuffer])

  return {
    vesselConnected: vesselWs.current?.readyState === WebSocket.OPEN,
    alertConnected: alertWs.current?.readyState === WebSocket.OPEN,
  }
}
