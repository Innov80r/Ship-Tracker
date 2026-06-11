import { create } from 'zustand'

const useUIStore = create((set) => ({
  sidebarOpen: false,
  vesselPanelOpen: false,
  layerControlOpen: false,
  searchOpen: false,

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleVesselPanel: () => set((s) => ({ vesselPanelOpen: !s.vesselPanelOpen })),
  openVesselPanel: () => set({ vesselPanelOpen: true }),
  closeVesselPanel: () => set({ vesselPanelOpen: false }),
  toggleLayerControl: () => set((s) => ({ layerControlOpen: !s.layerControlOpen })),
  openLayerControl: () => set({ layerControlOpen: true }),
  closeLayerControl: () => set({ layerControlOpen: false }),
  toggleSearch: () => set((s) => ({ searchOpen: !s.searchOpen })),
}))

export default useUIStore
