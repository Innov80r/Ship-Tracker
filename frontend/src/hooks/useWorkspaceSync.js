import { useEffect, useRef } from 'react'
import axios from 'axios'
import { useShallow } from 'zustand/react/shallow'
import useIntelStore, { defaultSharedWorkspaceNotes } from '../store/intelStore'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function hasMeaningfulSnapshot(snapshot) {
  if (!snapshot) return false

  return Boolean(
    snapshot.workspace_name && snapshot.workspace_name !== 'Aegis Maritime Command' ||
    snapshot.shared_workspace_notes && snapshot.shared_workspace_notes !== defaultSharedWorkspaceNotes ||
    snapshot.browser_notifications_enabled ||
    snapshot.watchlist_mmsis?.length ||
    snapshot.saved_searches?.length ||
    snapshot.fleets?.length ||
    Object.keys(snapshot.analyst_notes || {}).length ||
    snapshot.webhook_endpoints?.length,
  )
}

export default function useWorkspaceSync() {
  const workspaceState = useIntelStore(useShallow((state) => ({
    workspaceName: state.workspaceName,
    sharedWorkspaceNotes: state.sharedWorkspaceNotes,
    browserNotificationsEnabled: state.browserNotificationsEnabled,
    watchlistMmsis: state.watchlistMmsis,
    savedSearches: state.savedSearches,
    fleets: state.fleets,
    analystNotes: state.analystNotes,
    notificationRules: state.notificationRules,
    webhookEndpoints: state.webhookEndpoints,
  })))
  const hydrateWorkspaceSnapshot = useIntelStore((state) => state.hydrateWorkspaceSnapshot)
  const getWorkspaceSnapshotData = useIntelStore((state) => state.getWorkspaceSnapshotData)
  const setWorkspaceSyncState = useIntelStore((state) => state.setWorkspaceSyncState)

  const readyRef = useRef(false)
  const skipNextSaveRef = useRef(false)
  const saveTimerRef = useRef(null)

  useEffect(() => {
    let ignore = false

    const load = async () => {
      setWorkspaceSyncState('loading')
      try {
        const { data } = await axios.get(`${API}/api/workspace`)
        if (ignore || data?.error) {
          if (!ignore) setWorkspaceSyncState('error')
          return
        }

        const localSnapshot = useIntelStore.getState().getWorkspaceSnapshotData()
        let snapshotToHydrate = data

        if (!hasMeaningfulSnapshot(data) && hasMeaningfulSnapshot(localSnapshot)) {
          const saved = await axios.put(`${API}/api/workspace`, localSnapshot)
          if (!saved.data?.error) snapshotToHydrate = saved.data
        }

        if (!ignore) {
          skipNextSaveRef.current = true
          hydrateWorkspaceSnapshot(snapshotToHydrate)
          readyRef.current = true
          setWorkspaceSyncState('synced')
        }
      } catch {
        if (!ignore) {
          readyRef.current = true
          setWorkspaceSyncState('offline')
        }
      }
    }

    load()

    return () => {
      ignore = true
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [hydrateWorkspaceSnapshot, setWorkspaceSyncState])

  useEffect(() => {
    if (!readyRef.current) return
    if (skipNextSaveRef.current) {
      skipNextSaveRef.current = false
      return
    }

    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)

    saveTimerRef.current = setTimeout(async () => {
      setWorkspaceSyncState('saving')
      try {
        const snapshot = getWorkspaceSnapshotData()
        const { data } = await axios.put(`${API}/api/workspace`, snapshot)
        if (data?.error) {
          setWorkspaceSyncState('error')
          return
        }
        skipNextSaveRef.current = true
        hydrateWorkspaceSnapshot(data)
        setWorkspaceSyncState('synced')
      } catch {
        setWorkspaceSyncState('error')
      }
    }, 800)

    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [workspaceState, getWorkspaceSnapshotData, hydrateWorkspaceSnapshot, setWorkspaceSyncState])
}
