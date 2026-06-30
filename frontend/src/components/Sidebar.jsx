'use client'

const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', icon: '◧' },
  { key: 'live', label: 'Live Pipeline', icon: '◴' },
  { key: 'dataset', label: 'Dataset Upload', icon: '⇧' },
]

export default function Sidebar({ active, onSelect }) {
  return (
    <aside className="w-[220px] shrink-0 hidden lg:flex flex-col gap-6 py-6 pr-4">
      <div className="px-2">
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold"
            style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
          >
            W
          </div>
          <span className="font-semibold text-[0.95rem]">WallVision</span>
        </div>
      </div>

      <nav className="flex flex-col gap-1 px-1">
        {NAV_ITEMS.map((item) => (
          <div
            key={item.key}
            className={`nav-item ${active === item.key ? 'active' : ''}`}
            onClick={() => onSelect(item.key)}
          >
            <span>{item.icon}</span>
            {item.label}
          </div>
        ))}
      </nav>

      <div className="mt-auto px-2">
        <div className="card !p-3">
          <p className="text-[0.72rem] leading-relaxed" style={{ color: 'var(--text-dim)' }}>
            FMCW radar DSP pipeline — chirp simulation through micro-Doppler
            vital sign extraction.
          </p>
        </div>
      </div>
    </aside>
  )
}