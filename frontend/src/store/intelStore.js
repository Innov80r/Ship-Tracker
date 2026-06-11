import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

function uniqueValues(values) {
  return Array.from(new Set(values))
}

function createId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export const defaultRules = [
  { id: 'rule-distress', name: 'Distress escalation', event: 'distress', channel: 'browser', severity: 'critical', enabled: true },
  { id: 'rule-military', name: 'Military motion', event: 'military', channel: 'browser', severity: 'warning', enabled: true },
  { id: 'rule-dark', name: 'AIS silence', event: 'dark-vessel', channel: 'browser', severity: 'warning', enabled: false },
]

export const defaultSharedWorkspaceNotes = 'Shared workspace is local-first in this build. Export the workspace profile to pass it between operators.'

function defaultState() {
  return {
    workspaceId: null,
    workspaceSlug: 'default',
    workspaceName: 'Aegis Maritime Command',
    analystNotes: {},
    watchlistMmsis: [],
    savedSearches: [],
    fleets: [],
    notificationRules: defaultRules,
    webhookEndpoints: [],
    browserNotificationsEnabled: false,
    sharedWorkspaceNotes: defaultSharedWorkspaceNotes,
    workspaceSyncState: 'idle',
  }
}

function normalizeSnapshot(snapshot = {}) {
  return {
    workspaceId: snapshot.workspace_id ?? null,
    workspaceSlug: snapshot.workspace_slug ?? 'default',
    workspaceName: snapshot.workspace_name ?? 'Aegis Maritime Command',
    analystNotes: snapshot.analyst_notes ?? {},
    watchlistMmsis: snapshot.watchlist_mmsis ?? [],
    savedSearches: snapshot.saved_searches ?? [],
    fleets: snapshot.fleets ?? [],
    notificationRules: snapshot.notification_rules?.length ? snapshot.notification_rules : defaultRules,
    webhookEndpoints: snapshot.webhook_endpoints ?? [],
    browserNotificationsEnabled: Boolean(snapshot.browser_notifications_enabled),
    sharedWorkspaceNotes: snapshot.shared_workspace_notes ?? defaultSharedWorkspaceNotes,
  }
}

const useIntelStore = create(
  persist(
    (set, get) => ({
      ...defaultState(),

      setWorkspaceName: (workspaceName) => set({ workspaceName }),
      setSharedWorkspaceNotes: (sharedWorkspaceNotes) => set({ sharedWorkspaceNotes }),
      setWorkspaceSyncState: (workspaceSyncState) => set({ workspaceSyncState }),

      hydrateWorkspaceSnapshot: (snapshot) => set((state) => ({
        ...state,
        ...normalizeSnapshot(snapshot),
      })),

      toggleWatchlistVessel: (mmsi) => set((state) => {
        const next = state.watchlistMmsis.includes(mmsi)
          ? state.watchlistMmsis.filter((value) => value !== mmsi)
          : [...state.watchlistMmsis, mmsi]
        return { watchlistMmsis: uniqueValues(next) }
      }),
      clearWatchlist: () => set({ watchlistMmsis: [] }),

      setAnalystNote: (mmsi, note) => set((state) => ({
        analystNotes: {
          ...state.analystNotes,
          [mmsi]: note,
        },
      })),

      saveSearch: (name, filters) => set((state) => ({
        savedSearches: [
          {
            id: createId('search'),
            name,
            filters,
            created_at: new Date().toISOString(),
          },
          ...state.savedSearches,
        ].slice(0, 20),
      })),
      deleteSavedSearch: (id) => set((state) => ({
        savedSearches: state.savedSearches.filter((entry) => entry.id !== id),
      })),

      addFleet: (name, description = '') => set((state) => ({
        fleets: [
          ...state.fleets,
          {
            id: createId('fleet'),
            name,
            description,
            members: [],
            created_at: new Date().toISOString(),
          },
        ],
      })),
      updateFleet: (id, patch) => set((state) => ({
        fleets: state.fleets.map((fleet) => (
          fleet.id === id ? { ...fleet, ...patch } : fleet
        )),
      })),
      deleteFleet: (id) => set((state) => ({
        fleets: state.fleets.filter((fleet) => fleet.id !== id),
      })),
      addFleetMember: (fleetId, mmsi, note = '') => set((state) => ({
        fleets: state.fleets.map((fleet) => {
          if (fleet.id !== fleetId) return fleet
          if (fleet.members.some((member) => member.mmsi === mmsi)) return fleet
          return {
            ...fleet,
            members: [
              ...fleet.members,
              {
                id: createId('fleet-member'),
                mmsi,
                note,
                created_at: new Date().toISOString(),
              },
            ],
          }
        }),
      })),
      removeFleetMember: (fleetId, mmsi) => set((state) => ({
        fleets: state.fleets.map((fleet) => (
          fleet.id === fleetId
            ? { ...fleet, members: fleet.members.filter((member) => member.mmsi !== mmsi) }
            : fleet
        )),
      })),

      setBrowserNotificationsEnabled: (browserNotificationsEnabled) => set({ browserNotificationsEnabled }),

      addWebhookEndpoint: (endpoint) => set((state) => ({
        webhookEndpoints: [
          {
            id: createId('webhook'),
            enabled: true,
            ...endpoint,
            created_at: new Date().toISOString(),
          },
          ...state.webhookEndpoints,
        ].slice(0, 12),
      })),
      toggleWebhookEndpoint: (id) => set((state) => ({
        webhookEndpoints: state.webhookEndpoints.map((endpoint) =>
          endpoint.id === id ? { ...endpoint, enabled: !endpoint.enabled } : endpoint,
        ),
      })),
      removeWebhookEndpoint: (id) => set((state) => ({
        webhookEndpoints: state.webhookEndpoints.filter((endpoint) => endpoint.id !== id),
      })),

      toggleNotificationRule: (id) => set((state) => ({
        notificationRules: state.notificationRules.map((rule) =>
          rule.id === id ? { ...rule, enabled: !rule.enabled } : rule,
        ),
      })),
      updateNotificationRule: (id, patch) => set((state) => ({
        notificationRules: state.notificationRules.map((rule) =>
          rule.id === id ? { ...rule, ...patch } : rule,
        ),
      })),

      getWorkspaceSnapshotData: () => ({
        workspace_name: get().workspaceName,
        shared_workspace_notes: get().sharedWorkspaceNotes,
        browser_notifications_enabled: get().browserNotificationsEnabled,
        watchlist_mmsis: get().watchlistMmsis,
        saved_searches: get().savedSearches,
        fleets: get().fleets,
        analyst_notes: get().analystNotes,
        notification_rules: get().notificationRules,
        webhook_endpoints: get().webhookEndpoints,
      }),

      exportWorkspaceSnapshot: () => JSON.stringify(get().getWorkspaceSnapshotData(), null, 2),
    }),
    {
      name: 'sea-tracker-intel',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        workspaceId: state.workspaceId,
        workspaceSlug: state.workspaceSlug,
        workspaceName: state.workspaceName,
        analystNotes: state.analystNotes,
        watchlistMmsis: state.watchlistMmsis,
        savedSearches: state.savedSearches,
        fleets: state.fleets,
        notificationRules: state.notificationRules,
        webhookEndpoints: state.webhookEndpoints,
        browserNotificationsEnabled: state.browserNotificationsEnabled,
        sharedWorkspaceNotes: state.sharedWorkspaceNotes,
      }),
    },
  ),
)

export default useIntelStore
