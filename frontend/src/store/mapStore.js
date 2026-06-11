import { create } from 'zustand'

const useMapStore = create((set) => ({
  center: [30, 0],
  zoom: 3,
  selectedCountryKey: null,
  activeLayers: {
    vessels: true,
    openSeaMap: true,
    bathymetry: false,
    heatmap: false,
    trails: false,
    weather: false,
    waves: false,
    currents: false,
    tides: false,
    cables: false,
    eez: false,
    ports: true,
    incidents: true,
    zones: true,
    shippingLanes: false,
  },

  setCenter: (center) => set({ center }),
  setZoom: (zoom) => set({ zoom }),
  setSelectedCountryKey: (selectedCountryKey) => set({ selectedCountryKey }),
  toggleLayer: (layer) => set((state) => ({
    activeLayers: { ...state.activeLayers, [layer]: !state.activeLayers[layer] },
  })),
  setLayer: (layer, value) => set((state) => ({
    activeLayers: { ...state.activeLayers, [layer]: value },
  })),
  flyTo: (lat, lng, zoom = 12) => set({ center: [lat, lng], zoom }),
}))

export default useMapStore
