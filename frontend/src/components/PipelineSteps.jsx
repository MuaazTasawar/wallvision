'use client'

const STAGE_NAMES = [
  'Chirp Generation',
  'Range FFT',
  'Doppler FFT',
  'OS-CFAR Detection',
  'Micro-Doppler CWT',
  'Vital Sign Extraction',
]

/**
 * Animated stage tracker for the live WebSocket pipeline run.
 * `steps` is keyed by stage index ({0: {...}, 1: {...}, ...}) and fills
 * in as messages arrive from the backend, lighting up each card live.
 */
export default function PipelineSteps({ steps, running, summary }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className={`status-dot ${running ? 'processing' : 'idle'}`} /> Live Pipeline
      </div>

      <div className="flex flex-col gap-2">
        {STAGE_NAMES.map((name, idx) => {
          const done = steps[idx] !== undefined
          const isCurrent = running && !done && (idx === 0 || steps[idx - 1] !== undefined)
          return (
            <div
              key={idx}
              className="flex items-center gap-3 px-3 py-2 border border-scope-border rounded-sm"
              style={{
                borderColor: done ? 'var(--phosphor-dim)' : 'var(--border)',
                background: done ? 'var(--phosphor-glow)' : 'transparent',
              }}
            >
              <span
                className={`status-dot ${done ? 'detected' : isCurrent ? 'processing' : 'idle'}`}
              />
              <span className="mono" style={{ color: done ? 'var(--phosphor)' : 'var(--text-dim)' }}>
                {String(idx).padStart(2, '0')} — {name}
              </span>
            </div>
          )
        })}
      </div>

      {summary && (
        <p className="mono mt-4 pt-4 border-t border-scope-border">
          {summary.target_detected
            ? `Target locked — ${summary.num_detections} detection(s).`
            : 'No target detected this run.'}
        </p>
      )}
    </div>
  )
}