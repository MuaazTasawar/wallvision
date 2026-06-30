'use client'

export default function TargetPanel({ detections = [], breathingRate, heartRate, vitalsDetected }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className={`status-dot ${detections.length ? 'detected' : 'idle'}`} />
        Detections
      </div>

      {detections.length === 0 ? (
        <p className="mono text-scope-text-faint">No targets above CFAR threshold.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {detections.map((d, i) => (
            <div
              key={i}
              className="flex items-center justify-between border border-scope-border rounded-sm px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span className="badge badge-phosphor">T{i + 1}</span>
                <span className="mono text-scope-text">{d.range_m.toFixed(2)} m</span>
              </div>
              <div className="flex items-center gap-3 mono">
                <span>{d.velocity_mps.toFixed(2)} m/s</span>
                <span className="text-scope-phosphor">{d.snr_db.toFixed(1)} dB</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {vitalsDetected && (
        <div className="mt-5 pt-4 border-t border-scope-border grid grid-cols-2 gap-4">
          <div>
            <div className="metric-value">{breathingRate ?? '--'}</div>
            <div className="metric-label">Breathing BPM</div>
          </div>
          <div>
            <div className="metric-value amber">{heartRate ?? '--'}</div>
            <div className="metric-label">Heart Rate BPM</div>
          </div>
        </div>
      )}
    </div>
  )
}