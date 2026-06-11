import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import useAlertStore from '../../store/alertStore'
import useIncidentStore from '../../store/incidentStore'
import useIntelStore from '../../store/intelStore'
import useVesselStore from '../../store/vesselStore'
import SearchBar from '../search/SearchBar'

const NAV_ITEMS = [
  { path: '/', label: 'Ops Map' },
  { path: '/dashboard', label: 'Intel' },
  { path: '/history', label: 'Playback' },
  { path: '/incidents', label: 'Signals' },
  { path: '/alerts', label: 'Alerts' },
  { path: '/ports', label: 'Ports' },
  { path: '/statistics', label: 'Fleet Atlas' },
  { path: '/reports', label: 'Reports' },
  { path: '/workspace', label: 'Workspace' },
]

export default function Navbar() {
  const location = useLocation()
  const unreadCount = useAlertStore((state) => state.unreadCount)
  const activeCount = useIncidentStore((state) => state.activeCount)
  const vesselCount = useVesselStore((state) => state.vesselCount)
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const workspaceName = useIntelStore((state) => state.workspaceName)

  return (
    <header className="relative z-50 px-4 pt-4 md:px-6 md:pt-6" id="main-nav">
      <div className="panel-surface border-white/5 bg-[rgba(3,7,18,0.8)]">
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-start gap-4">
              <Link to="/" className="flex items-center gap-4">
                <div className="brand-core">
                  <div className="brand-core__pulse" />
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="text-cyan-100">
                    <path d="M3 16c2.2-1.6 4.1-2.4 5.8-2.4 1.8 0 3.4.7 5 2.2 1.7 1.5 3.4 2.2 5.2 2.2H21" />
                    <path d="M4 12c1.8-1.4 3.6-2.1 5.3-2.1 1.6 0 3.2.6 4.6 1.9 1.5 1.2 3.2 1.9 5.1 1.9H21" />
                    <path d="M5 8h8l2 4h4" />
                  </svg>
                </div>
                <div>
                  <div className="eyebrow">Future maritime intelligence</div>
                  <div className="mt-1 text-2xl font-semibold tracking-tight text-white">Sea Tracker Command</div>
                  <div className="mt-1 text-sm text-slate-500">{workspaceName}</div>
                </div>
              </Link>
            </div>

            <div className="grid w-full grid-cols-2 gap-2 sm:w-auto sm:grid-cols-4">
              <StatusChip label="Tracked" value={vesselCount.toLocaleString()} tone="cyan" />
              <StatusChip label="Pinned" value={watchlistMmsis.length} tone="emerald" />
              <StatusChip label="Alerts" value={unreadCount} tone="amber" />
              <StatusChip label="Signals" value={activeCount} tone="rose" />
            </div>
          </div>

          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <nav className="hide-scrollbar flex items-center gap-2 overflow-x-auto">
              {NAV_ITEMS.map((item) => {
                const active = location.pathname === item.path
                return (
                  <Link key={item.path} to={item.path} className={`command-link ${active ? 'command-link--active' : ''}`}>
                    {item.label}
                    {item.path === '/alerts' && unreadCount > 0 && (
                      <span className="command-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
                    )}
                    {item.path === '/incidents' && activeCount > 0 && (
                      <span className="command-badge command-badge--rose">{activeCount}</span>
                    )}
                  </Link>
                )
              })}
            </nav>

            <div className="w-full xl:w-[32rem]">
              <SearchBar />
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}

function StatusChip({ label, value, tone = 'cyan' }) {
  const toneClass = {
    cyan: 'status-chip--cyan',
    emerald: 'status-chip--emerald',
    amber: 'status-chip--amber',
    rose: 'status-chip--rose',
  }

  return (
    <div className={`status-chip ${toneClass[tone] || toneClass.cyan}`}>
      <div className="status-chip__halo" />
      <div className="status-chip__header">
        <span className="status-chip__dot" />
        <span className="status-chip__label">{label}</span>
      </div>
      <div className="status-chip__value font-mono">{value}</div>
    </div>
  )
}
