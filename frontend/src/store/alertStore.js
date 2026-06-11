import { create } from 'zustand'

const useAlertStore = create((set, get) => ({
  alerts: [],
  unreadCount: 0,

  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts].slice(0, 200),
    unreadCount: state.unreadCount + 1,
  })),

  setAlerts: (alerts) => set({ alerts }),
  setUnreadCount: (count) => set({ unreadCount: count }),

  markRead: (id) => set((state) => ({
    alerts: state.alerts.map(a => a.id === id ? { ...a, is_read: true } : a),
    unreadCount: Math.max(0, state.unreadCount - 1),
  })),

  markAllRead: () => set((state) => ({
    alerts: state.alerts.map(a => ({ ...a, is_read: true })),
    unreadCount: 0,
  })),
}))

export default useAlertStore
