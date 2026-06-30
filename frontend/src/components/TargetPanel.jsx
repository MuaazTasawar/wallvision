'use client'

export default function TargetPanel({ detections = [], breathingRate, heartRate, vitalsDetected }) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-1">
        <span className={`dot ${detections.length ? 'on' : 'off'}`} />
        <span className="card-title !mb-0">Detections</span>
      </div>
      <div className="card-subtitle">Targets above the CFAR threshold</div>

      {detections.length === 0 ? (
        <p className="text-[0.82rem]" style={{ color: 'var(--text-dim)' }}>No targets detected.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {detections.map((d, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-xl px-3 py-2.5"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
            >
              <div className="flex items-center gap-2.5">
                <span className="pill active">T{i + 1}</span>
                <span className="text-[0.85rem] font-medium">{d.range_m.toFixed(2)} m</span>
              </div>
              <div className="flex items-center gap-3 text-[0.78rem]" style={{ color: 'var(--text-dim)' }}>
                <span>{d.velocity_mps.toFixed(2)} m/s</span>
                <span className="pill good">{d.snr_db.toFixed(1)} dB</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {vitalsDetected && (
        <div className="mt-5 pt-4 grid grid-cols-2 gap-4" style={{ borderTop: '1px solid var(--border)' }}>
          <div>
            <div className="text-3xl font-bold">{breathingRate ?? '--'}</div>
            <div className="text-[0.7rem] mt-1" style={{ color: 'var(--text-dim)' }}>Breathing BPM</div>
          </div>
          <div>
            <div className="text-3xl font-bold" style={{ color: 'var(--warn)' }}>{heartRate ?? '--'}</div>
            <div className="text-[0.7rem] mt-1" style={{ color: 'var(--text-dim)' }}>Heart Rate BPM</div>
          </div>
        </div>
      )}
    </div>
  )
}