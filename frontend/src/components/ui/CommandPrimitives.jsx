import React from 'react'

const TONE_CLASS = {
  cyan: 'from-cyan-400/30 to-cyan-500/5 border-cyan-400/20 text-cyan-100',
  emerald: 'from-emerald-400/30 to-emerald-500/5 border-emerald-400/20 text-emerald-100',
  amber: 'from-amber-400/30 to-amber-500/5 border-amber-400/20 text-amber-100',
  rose: 'from-rose-400/30 to-rose-500/5 border-rose-400/20 text-rose-100',
  violet: 'from-violet-400/30 to-violet-500/5 border-violet-400/20 text-violet-100',
  slate: 'from-slate-300/20 to-slate-500/5 border-slate-400/20 text-slate-100',
}

export function PageHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="space-y-2">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">{title}</h1>
          {subtitle && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Panel({ title, subtitle, action, className = '', children }) {
  return (
    <section className={`panel-surface ${className}`.trim()}>
      {(title || action) && (
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            {title && <h2 className="text-sm font-semibold tracking-wide text-white">{title}</h2>}
            {subtitle && <p className="mt-1 text-xs leading-5 text-slate-400">{subtitle}</p>}
          </div>
          {action && <div className="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:shrink-0 lg:justify-end">{action}</div>}
        </div>
      )}
      {children}
    </section>
  )
}

export function StatTile({ label, value, caption, tone = 'cyan' }) {
  return (
    <div className={`metric-shell min-h-[8.75rem] p-4 bg-gradient-to-br ${TONE_CLASS[tone] || TONE_CLASS.cyan}`}>
      <div className="text-[10px] uppercase tracking-[0.18em] text-slate-400">{label}</div>
      <div className="mt-3 text-[2rem] font-semibold leading-none tracking-tight">{value}</div>
      {caption && <div className="mt-2 text-[11px] leading-5 text-slate-400">{caption}</div>}
    </div>
  )
}

export function Pill({ children, tone = 'slate' }) {
  const toneClass = {
    cyan: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-100',
    emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100',
    amber: 'border-amber-400/20 bg-amber-400/10 text-amber-100',
    rose: 'border-rose-400/20 bg-rose-400/10 text-rose-100',
    slate: 'border-slate-500/20 bg-slate-500/10 text-slate-200',
  }

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] ${toneClass[tone] || toneClass.slate}`}>
      {children}
    </span>
  )
}

export function EmptyState({ title, message }) {
  return (
    <div className="flex min-h-40 items-center justify-center rounded-2xl border border-dashed border-slate-700/80 bg-slate-950/25 px-6 py-8 text-center">
      <div>
        <div className="text-base font-semibold text-slate-200">{title}</div>
        <div className="mt-2 text-sm leading-6 text-slate-500">{message}</div>
      </div>
    </div>
  )
}

export function DataRow({ title, subtitle, value, tone = 'slate', onClick, action }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`intel-row ${onClick ? 'cursor-pointer hover:border-cyan-400/20 hover:bg-cyan-400/5' : 'cursor-default'}`}
    >
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-white">{title}</div>
        {subtitle && <div className="mt-1 truncate text-xs text-slate-500">{subtitle}</div>}
      </div>
      <div className="flex items-center gap-3">
        {value && <Pill tone={tone}>{value}</Pill>}
        {action}
      </div>
    </button>
  )
}
