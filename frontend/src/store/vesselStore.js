import { create } from 'zustand'

function getFreshnessTimestamp(vessel, fallback = 0) {
  const serverTimestamp = vessel?.last_updated ? Date.parse(vessel.last_updated) : NaN
  if (Number.isFinite(serverTimestamp)) return serverTimestamp
  return Number.isFinite(vessel?._updated) ? vessel._updated : fallback
}

function mergeVesselUpdates(currentVessels, vesselList) {
  const nextVessels = { ...currentVessels }
  const updatedAt = Date.now()
  let addedCount = 0

  vesselList.forEach((vessel) => {
    if (!(vessel.mmsi in nextVessels)) addedCount += 1
    nextVessels[vessel.mmsi] = {
      ...nextVessels[vessel.mmsi],
      ...vessel,
      _updated: getFreshnessTimestamp(vessel, updatedAt),
    }
  })

  return { nextVessels, addedCount }
}

function syncSelectedVessel(selectedVessel, nextVessels) {
  if (!selectedVessel?.mmsi) return selectedVessel
  return nextVessels[selectedVessel.mmsi] || null
}

const useVesselStore = create((set, get) => ({
  vessels: {},
  selectedVessel: null,
  vesselCount: 0,

  updateVessel: (vessel) => set((state) => {
    const { nextVessels, addedCount } = mergeVesselUpdates(state.vessels, [vessel])
    return {
      vessels: nextVessels,
      selectedVessel: syncSelectedVessel(state.selectedVessel, nextVessels),
      vesselCount: state.vesselCount + addedCount,
    }
  }),

  updateVesselBatch: (vesselList) => set((state) => {
    if (!vesselList.length) return state
    const { nextVessels, addedCount } = mergeVesselUpdates(state.vessels, vesselList)
    return {
      vessels: nextVessels,
      selectedVessel: syncSelectedVessel(state.selectedVessel, nextVessels),
      vesselCount: state.vesselCount + addedCount,
    }
  }),

  updateVessels: (vesselList) => set(() => {
    const map = {}
    const fallbackTimestamp = Date.now()
    vesselList.forEach((vessel) => {
      map[vessel.mmsi] = {
        ...vessel,
        _updated: getFreshnessTimestamp(vessel, fallbackTimestamp),
      }
    })
    const currentSelectedVessel = get().selectedVessel
    return {
      vessels: map,
      selectedVessel: syncSelectedVessel(currentSelectedVessel, map),
      vesselCount: vesselList.length,
    }
  }),

  selectVessel: (mmsi) => set((state) => ({
    selectedVessel: mmsi ? state.vessels[mmsi] || null : null,
  })),

  clearSelection: () => set({ selectedVessel: null }),

  removeStale: (timeoutMs = 600000) => set((state) => {
    const now = Date.now()
    const active = {}
    Object.entries(state.vessels).forEach(([mmsi, v]) => {
      if (now - getFreshnessTimestamp(v) < timeoutMs) active[mmsi] = v
    })
    return {
      vessels: active,
      selectedVessel: syncSelectedVessel(state.selectedVessel, active),
      vesselCount: Object.keys(active).length,
    }
  }),

  getVesselArray: () => Object.values(get().vessels),
}))

export default useVesselStore
