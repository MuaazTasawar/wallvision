'use client'

const STAGE_NAMES = ['Chirp Generation', 'Range FFT', 'Doppler FFT', 'OS-CFAR Detection', 'Micro-Doppler CWT', 'Vital Sign Extraction']

export default function PipelineSteps({ steps, running, summary }) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-1">
        <span className={`dot ${running ? 'busy' : 'off'}`} />
        <span className="card-title !mb-0">Live Pipeline</span>
      </div>
      <div className="card-subtitle">Stage-by-stage processing status</div>

      <div className="flex flex-col gap-2">
        {STAGE_NAMES.map((name, idx) => {
          const done = steps[idx] !== undefined
          const isCurrent = running && !done && (idx === 0 || steps[idx - 1] !== undefined)
          return (
            <div
              key={idx}
              className="flex items-center gap-3 px-3 py-2 rounded-xl"
              style={{
                border: '1px solid var(--border)',
                background: done ? 'var(--surface)' : 'transparent',
              }}
            >
              <span className={`dot ${done ? 'on' : isCurrent ? 'busy' : 'off'}`} />
              <span className="text-[0.8rem]" style={{ color: done ? 'var(--text)' : 'var(--text-dim)', fontWeight: done ? 600 : 400 }}>
                {String(idx).padStart(2, '0')} — {name}
              </span>
            </div>
          )
        })}
      </div>

      {summary && (
        <p className="text-[0.78rem] mt-4 pt-4" style={{ borderTop: '1px solid var(--border)', color: 'var(--text-dim)' }}>
          {summary.target_detected ? `Target locked — ${summary.num_detections} detection(s).` : 'No target detected.'}
        </p>
      )}
    </div>
  )
}