import React from 'react'
import useCoverageDiagnostics from '../../hooks/useCoverageDiagnostics'
import useIncidentStore from '../../store/incidentStore'
import useIntelStore from '../../store/intelStore'
import useVesselStore from '../../store/vesselStore'

export default function StatusBar() {
  const vesselCount = useVesselStore((state) => state.vesselCount)
  const hasMayday = useIncidentStore((state) => state.hasMayday)
  const workspaceName = useIntelStore((state) => state.workspaceName)
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const { health, coverage } = useCoverageDiagnostics(true)
  const liveConnected = health.status === 'healthy'
  const activeSources = health.active_sources || []
  const primaryWarning = coverage.warnings?.[0]

  return (
    <>
      {hasMayday && (
        <div className="mayday-banner" id="mayday-banner">
          MAYDAY - ACTIVE DISTRESS SIGNAL DETECTED - MAYDAY
        </div>
      )}
      {primaryWarning && (
        <div className="mx-4 mb-3 rounded-[1.25rem] border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-xs text-amber-100 md:mx-6" id="coverage-warning">
          <span className="font-semibold uppercase tracking-[0.18em] text-amber-200">Coverage Notice</span>
          <span className="ml-3">{primaryWarning}</span>
        </div>
      )}
      <footer className="relative z-10 px-4 pb-4 md:px-6 md:pb-6" id="status-bar">
        <div className="surface-strip justify-between text-[11px] text-slate-500">
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-2">
              <span className={`indicator-dot ${liveConnected ? 'active' : ''}`} />
              {liveConnected ? 'Live feed connected' : 'Live feed unavailable'}
            </span>
            <span>{vesselCount.toLocaleString()} tracked</span>
            <span>{watchlistMmsis.length} pinned</span>
            <span>{coverage.unique_flag_countries || 0} flags</span>
            <span>{workspaceName}</span>
          </div>
          <div className="hidden items-center gap-3 lg:flex">
            {activeSources.length > 0 ? (
              activeSources.map((source) => (
                <span key={source}>{source}</span>
              ))
            ) : (
              <span>No active AIS sources</span>
            )}
            <span>{coverage.active_source_count || 0} active source{coverage.active_source_count === 1 ? '' : 's'}</span>
            <span>{Math.round((coverage.top_source_share || 0) * 100)}% primary source share</span>
          </div>
        </div>
      </footer>
    </>
  )
}
