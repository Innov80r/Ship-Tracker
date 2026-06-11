import React from 'react'

export default function Sidebar({ children, title, open, onClose }) {
  if (!open) return null
  return (
    <div className="absolute top-0 left-0 h-full w-80 glass-panel z-[1100] flex flex-col slide-in-right" id="sidebar">
      <div className="flex items-center justify-between p-4 border-b border-navy-600">
        <h2 className="font-semibold text-ocean-400">{title}</h2>
        <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">&times;</button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">{children}</div>
    </div>
  )
}
