import { create } from 'zustand'

const useIncidentStore = create((set) => ({
  incidents: [],
  activeCount: 0,
  hasMayday: false,

  setIncidents: (incidents) => set({
    incidents,
    activeCount: incidents.filter(i => i.is_active).length,
    hasMayday: incidents.some(i => i.is_active && (i.incident_type === 'MAYDAY' || i.incident_type === 'AIS_SART')),
  }),

  addIncident: (incident) => set((state) => {
    const updated = [incident, ...state.incidents]
    return {
      incidents: updated,
      activeCount: updated.filter(i => i.is_active).length,
      hasMayday: updated.some(i => i.is_active && (i.incident_type === 'MAYDAY' || i.incident_type === 'AIS_SART')),
    }
  }),

  resolveIncident: (id) => set((state) => {
    const updated = state.incidents.map(i => i.id === id ? { ...i, is_active: false, is_resolved: true } : i)
    return {
      incidents: updated,
      activeCount: updated.filter(i => i.is_active).length,
      hasMayday: updated.some(i => i.is_active && (i.incident_type === 'MAYDAY' || i.incident_type === 'AIS_SART')),
    }
  }),
}))

export default useIncidentStore
