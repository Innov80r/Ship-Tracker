import React from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ToastContainer } from 'react-toastify'
import Navbar from './components/layout/Navbar'
import StatusBar from './components/layout/StatusBar'
import useAlerts from './hooks/useAlerts'
import useIncidents from './hooks/useIncidents'
import useVessels from './hooks/useVessels'
import useWebSocket from './hooks/useWebSocket'
import useWorkspaceSync from './hooks/useWorkspaceSync'
import AlertsPage from './pages/AlertsPage'
import DashboardPage from './pages/DashboardPage'
import HistoryPage from './pages/HistoryPage'
import IncidentsPage from './pages/IncidentsPage'
import MapPage from './pages/MapPage'
import PortsPage from './pages/PortsPage'
import ReportsPage from './pages/ReportsPage'
import StatisticsPage from './pages/StatisticsPage'
import WorkspacePage from './pages/WorkspacePage'

export default function App() {
  useVessels()
  useAlerts()
  useIncidents()
  useWebSocket()
  useWorkspaceSync()

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="app-shell">
        <div className="app-shell__background">
          <div className="app-shell__grid" />
          <div className="app-shell__glow app-shell__glow--left" />
          <div className="app-shell__glow app-shell__glow--right" />
        </div>

        <Navbar />

        <main className="relative z-10 min-h-0 flex-1 overflow-hidden px-4 pb-4 md:px-6 md:pb-6">
          <div className="h-full overflow-hidden rounded-[2.25rem] border border-white/5 bg-[rgba(2,6,23,0.45)] shadow-[0_30px_80px_rgba(2,6,23,0.52)]">
            <Routes>
              <Route path="/" element={<MapPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/incidents" element={<IncidentsPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/ports" element={<PortsPage />} />
              <Route path="/statistics" element={<StatisticsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/workspace" element={<WorkspacePage />} />
            </Routes>
          </div>
        </main>

        <StatusBar />

        <ToastContainer
          position="bottom-right"
          autoClose={5000}
          theme="dark"
          toastStyle={{
            background: 'rgba(3, 7, 18, 0.94)',
            border: '1px solid rgba(148, 163, 184, 0.16)',
            fontSize: '13px',
            borderRadius: '18px',
            color: '#f8fafc',
          }}
        />
      </div>
    </BrowserRouter>
  )
}
