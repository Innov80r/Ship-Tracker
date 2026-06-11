import React from 'react'
import useIntelStore from '../store/intelStore'
import { PageHeader, Panel, Pill, StatTile } from '../components/ui/CommandPrimitives'
import { exportAsJSON } from '../utils/exportHelpers'

export default function WorkspacePage() {
  const workspaceName = useIntelStore((state) => state.workspaceName)
  const setWorkspaceName = useIntelStore((state) => state.setWorkspaceName)
  const sharedWorkspaceNotes = useIntelStore((state) => state.sharedWorkspaceNotes)
  const setSharedWorkspaceNotes = useIntelStore((state) => state.setSharedWorkspaceNotes)
  const watchlistMmsis = useIntelStore((state) => state.watchlistMmsis)
  const savedSearches = useIntelStore((state) => state.savedSearches)
  const analystNotes = useIntelStore((state) => state.analystNotes)
  const webhookEndpoints = useIntelStore((state) => state.webhookEndpoints)
  const fleets = useIntelStore((state) => state.fleets)
  const addFleet = useIntelStore((state) => state.addFleet)
  const deleteFleet = useIntelStore((state) => state.deleteFleet)
  const updateFleet = useIntelStore((state) => state.updateFleet)
  const addFleetMember = useIntelStore((state) => state.addFleetMember)
  const removeFleetMember = useIntelStore((state) => state.removeFleetMember)
  const exportWorkspaceSnapshot = useIntelStore((state) => state.exportWorkspaceSnapshot)
  const workspaceSyncState = useIntelStore((state) => state.workspaceSyncState)
  const workspaceId = useIntelStore((state) => state.workspaceId)

  const handleExport = () => {
    exportAsJSON(JSON.parse(exportWorkspaceSnapshot()), `workspace_${Date.now()}.json`)
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(exportWorkspaceSnapshot())
  }

  const handleAddFleet = () => {
    const name = window.prompt('Fleet name')
    if (!name) return
    const description = window.prompt('Fleet description', '') || ''
    addFleet(name, description)
  }

  const handleAddFleetMember = (fleetId) => {
    const mmsiValue = window.prompt('Vessel MMSI')
    if (!mmsiValue) return
    const mmsi = Number(mmsiValue)
    if (!Number.isFinite(mmsi) || mmsi <= 0) return
    const note = window.prompt('Optional member note', '') || ''
    addFleetMember(fleetId, mmsi, note)
  }

  return (
    <div className="page-scroll" id="workspace-page">
      <PageHeader
        eyebrow="Workspace"
        title="Shared Workspace"
        subtitle="The workspace now syncs to the backend snapshot API. Watchlists, saved searches, fleets, notes, notification rules, and webhook presets are persisted in PostgreSQL."
        actions={(
          <>
            <Pill tone={workspaceSyncState === 'synced' ? 'emerald' : workspaceSyncState === 'saving' || workspaceSyncState === 'loading' ? 'amber' : 'rose'}>
              {workspaceSyncState}
            </Pill>
            <button type="button" className="btn-ghost" onClick={handleCopy}>Copy workspace JSON</button>
            <button type="button" className="btn-primary" onClick={handleExport}>Export workspace</button>
          </>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatTile label="Workspace ID" value={workspaceId ?? '—'} caption="Default persisted workspace" tone="cyan" />
        <StatTile label="Watchlist" value={watchlistMmsis.length} caption="Pinned contacts in workspace" tone="cyan" />
        <StatTile label="Saved searches" value={savedSearches.length} caption="Mission presets and filter packs" tone="emerald" />
        <StatTile label="Fleets" value={fleets.length} caption="Persisted fleet collections" tone="amber" />
        <StatTile label="Webhook presets" value={webhookEndpoints.length} caption="Configured outbound endpoints" tone="rose" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Workspace identity" subtitle="Name the operating workspace and keep the mission context explicit">
          <label className="block">
            <div className="eyebrow-sm">Workspace name</div>
            <input
              type="text"
              value={workspaceName}
              onChange={(event) => setWorkspaceName(event.target.value)}
              className="input-field mt-2 w-full"
              placeholder="Aegis Maritime Command"
            />
          </label>
          <div className="mt-4 flex flex-wrap gap-2">
            <Pill tone="cyan">Backend persisted</Pill>
            <Pill tone="emerald">Exportable</Pill>
            <Pill tone="amber">Analyst notes</Pill>
          </div>
        </Panel>

        <Panel title="Shared operating note" subtitle="A team-level note that ships with the backend and export payload">
          <textarea
            value={sharedWorkspaceNotes}
            onChange={(event) => setSharedWorkspaceNotes(event.target.value)}
            className="input-field min-h-36 w-full resize-y"
            placeholder="Capture mission scope, maritime chokepoints under watch, escalation rules, or handoff instructions for the next operator."
          />
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Panel
          title="Fleet registry"
          subtitle="Create persistent fleets and assign vessel MMSIs to them."
          action={<button type="button" className="btn-primary" onClick={handleAddFleet}>Add fleet</button>}
        >
          {fleets.length === 0 ? (
            <div className="text-sm text-slate-500">No fleets created yet. Add a fleet to start grouping vessels beyond watchlists.</div>
          ) : (
            <div className="space-y-3">
              {fleets.map((fleet) => (
                <div key={fleet.id} className="rounded-[1.25rem] border border-slate-800/90 bg-slate-950/35 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-white">{fleet.name}</div>
                      <div className="mt-1 text-xs text-slate-500">{fleet.description || 'No description'}</div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Pill tone="cyan">{fleet.members.length} members</Pill>
                      <button type="button" className="btn-ghost" onClick={() => {
                        const name = window.prompt('Fleet name', fleet.name)
                        if (!name) return
                        const description = window.prompt('Fleet description', fleet.description || '') ?? fleet.description
                        updateFleet(fleet.id, { name, description })
                      }}>
                        Rename
                      </button>
                      <button type="button" className="btn-ghost" onClick={() => handleAddFleetMember(fleet.id)}>
                        Add member
                      </button>
                      <button type="button" className="btn-ghost" onClick={() => deleteFleet(fleet.id)}>
                        Delete
                      </button>
                    </div>
                  </div>
                  {fleet.members.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {fleet.members.map((member) => (
                        <button
                          key={`${fleet.id}-${member.mmsi}`}
                          type="button"
                          onClick={() => removeFleetMember(fleet.id, member.mmsi)}
                          className="rounded-full border border-slate-700/80 bg-slate-900/60 px-3 py-1.5 text-[11px] font-medium text-slate-300 transition hover:border-rose-400/30 hover:text-rose-200"
                        >
                          MMSI {member.mmsi}{member.note ? ` · ${member.note}` : ''}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Workspace payload" subtitle="Preview of the exact snapshot being synced to the backend">
          <pre className="max-h-[38rem] overflow-x-auto overflow-y-auto rounded-[1.5rem] border border-slate-800/90 bg-slate-950/55 p-4 text-xs leading-6 text-slate-300">
            {exportWorkspaceSnapshot()}
          </pre>
        </Panel>
      </div>

      <Panel title="Workspace contents" subtitle="A quick breakdown of persisted operator state">
        <div className="flex flex-wrap gap-2">
          <Pill tone="cyan">{watchlistMmsis.length} watchlist</Pill>
          <Pill tone="emerald">{savedSearches.length} saved searches</Pill>
          <Pill tone="amber">{Object.keys(analystNotes).length} notes</Pill>
          <Pill tone="rose">{webhookEndpoints.length} webhooks</Pill>
          <Pill tone="slate">{fleets.length} fleets</Pill>
        </div>
      </Panel>
    </div>
  )
}
