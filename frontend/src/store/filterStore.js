import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export const defaultFilters = {
  searchQuery: '',
  vesselCategories: [],
  vesselTypes: [],
  flagCountries: [],
  navStatuses: [],
  dataSources: [],
  speedRange: [0, 45],
  draughtRange: [0, 20],
  lengthRange: [0, 400],
  lastSeenMaxMinutes: 360,
  riskMinimum: 0,
  watchlistOnly: false,
  darkOnly: false,
  weatherImpactOnly: false,
  destinationRequired: false,
}

export const selectFilterSnapshot = (state) => ({
  searchQuery: state.searchQuery,
  vesselCategories: state.vesselCategories,
  vesselTypes: state.vesselTypes,
  flagCountries: state.flagCountries,
  navStatuses: state.navStatuses,
  dataSources: state.dataSources,
  speedRange: state.speedRange,
  draughtRange: state.draughtRange,
  lengthRange: state.lengthRange,
  lastSeenMaxMinutes: state.lastSeenMaxMinutes,
  riskMinimum: state.riskMinimum,
  watchlistOnly: state.watchlistOnly,
  darkOnly: state.darkOnly,
  weatherImpactOnly: state.weatherImpactOnly,
  destinationRequired: state.destinationRequired,
})

const useFilterStore = create(
  persist(
    (set) => ({
      ...defaultFilters,

      setSearchQuery: (searchQuery) => set({ searchQuery }),
      setVesselCategories: (vesselCategories) => set({ vesselCategories }),
      setVesselTypes: (vesselTypes) => set({ vesselTypes }),
      setFlagCountries: (flagCountries) => set({ flagCountries }),
      setNavStatuses: (navStatuses) => set({ navStatuses }),
      setDataSources: (dataSources) => set({ dataSources }),
      setSpeedRange: (speedRange) => set({ speedRange }),
      setDraughtRange: (draughtRange) => set({ draughtRange }),
      setLengthRange: (lengthRange) => set({ lengthRange }),
      setLastSeenMaxMinutes: (lastSeenMaxMinutes) => set({ lastSeenMaxMinutes }),
      setRiskMinimum: (riskMinimum) => set({ riskMinimum }),
      toggleWatchlistOnly: () => set((state) => ({ watchlistOnly: !state.watchlistOnly })),
      toggleDarkOnly: () => set((state) => ({ darkOnly: !state.darkOnly })),
      toggleWeatherImpactOnly: () => set((state) => ({ weatherImpactOnly: !state.weatherImpactOnly })),
      toggleDestinationRequired: () => set((state) => ({ destinationRequired: !state.destinationRequired })),
      patchFilters: (patch) => set((state) => ({ ...state, ...patch })),
      clearFilters: () => set({ ...defaultFilters }),
    }),
    {
      name: 'sea-tracker-filters',
      storage: createJSONStorage(() => localStorage),
    },
  ),
)

export default useFilterStore
