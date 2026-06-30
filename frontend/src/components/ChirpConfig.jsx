'use client'

const FIELDS = [
  { key: 'bandwidth_ghz', label: 'Bandwidth', unit: 'GHz', min: 0.1, max: 4.0, step: 0.1 },
  { key: 'center_freq_ghz', label: 'Centre Freq', unit: 'GHz', min: 24, max: 81, step: 1 },
  { key: 'target_range_m', label: 'Target Range', unit: 'm', min: 0.5, max: 20, step: 0.1 },
  { key: 'target_velocity_mps', label: 'Velocity', unit: 'm/s', min: -5, max: 5, step: 0.1 },
  { key: 'snr_db', label: 'SNR', unit: 'dB', min: 0, max: 50, step: 1 },
  { key: 'breathing_rate_bpm', label: 'Breathing Rate', unit: 'BPM', min: 5, max: 40, step: 1 },
  { key: 'breathing_amplitude_mm', label: 'Chest Disp.', unit: 'mm', min: 0.1, max: 10, step: 0.1 },
]

export default function ChirpConfig({ config, onChange, onRun, onRunLive, loading, running, wsConnected }) {
  return (
    <div className="card">
      <div className="card-title">Scene Configuration</div>
      <div className="card-subtitle">Adjust the simulated radar scene</div>

      <div className="flex flex-col gap-4">
        {FIELDS.map((f) => (
          <div key={f.key}>
            <div className="flex justify-between items-baseline mb-1.5">
              <span className="text-[0.78rem]" style={{ color: 'var(--text-dim)' }}>{f.label}</span>
              <span className="text-[0.78rem] font-semibold">{config[f.key]} {f.unit}</span>
            </div>
            <input
              type="range"
              min={f.min} max={f.max} step={f.step}
              value={config[f.key]}
              onChange={(e) => onChange({ [f.key]: parseFloat(e.target.value) })}
            />
          </div>
        ))}

        <label className="flex items-center gap-2 text-[0.78rem] mt-1 cursor-pointer select-none" style={{ color: 'var(--text-dim)' }}>
          <input
            type="checkbox"
            checked={config.enable_heartbeat}
            onChange={(e) => onChange({ enable_heartbeat: e.target.checked })}
            className="w-3.5 h-3.5"
          />
          Include heartbeat micro-Doppler
        </label>
      </div>

      <div className="flex flex-col gap-2 mt-6 pt-5" style={{ borderTop: '1px solid var(--border)' }}>
        <button className="btn-primary w-full" disabled={loading} onClick={onRun}>
          {loading ? 'Processing...' : 'Run Simulation'}
        </button>
        <button className="btn-secondary w-full" disabled={running || !wsConnected} onClick={onRunLive}>
          {running ? 'Streaming...' : 'Run Live Pipeline'}
        </button>
      </div>
    </div>
  )
}