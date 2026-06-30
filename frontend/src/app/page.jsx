'use client'

import { usePipeline } from '@/hooks/usePipeline'
import { useWebSocket } from '@/hooks/useWebSocket'

export default function Home() {
  const { config, updateConfig, result, loading, error, runSimulation } = usePipeline()
  const { connected, steps, summary, running, wsError, runPipeline } = useWebSocket()

  return (
    <main className="min-h-screen px-6 py-8 max-w-[1400px] mx-auto">
      {/* ── Header ──────────────────────────────────────────── */}
      <header className="flex items-end justify-between mb-8 pb-5 border-b border-scope-border">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-scope-text">
            WALLVISION
          </h1>
          <p className="mono mt-1">FMCW Radar Signal Processing — Through-Wall Human Detection</p>
        </div>
        <div className="flex items-center gap-2 mono">
          <span className={`status-dot ${connected ? 'online' : 'idle'}`} />
          {connected ? 'LINK ESTABLISHED' : 'CONNECTING...'}
        </div>
      </header>

      {/* ── Placeholder grid — populated in Phase 6/7 ──────────── */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-3 panel">
          <div className="panel-header">
            <span className="status-dot idle" /> Chirp Config
          </div>
          <p className="mono">Sliders arrive in Phase 6.</p>
        </div>

        <div className="col-span-12 lg:col-span-9 panel">
          <div className="panel-header">
            <span className={`status-dot ${running ? 'processing' : 'idle'}`} /> Range-Doppler Map
          </div>
          <p className="mono">
            {error || wsError
              ? `Error: ${error || wsError}`
              : result
              ? `Last simulation: peak range present in response, ${result.detections.length} detection(s).`
              : 'Plotly visualization arrives in Phase 6.'}
          </p>
        </div>
      </div>

      <div className="mt-4 flex gap-3">
        <button className="btn-primary" disabled={loading} onClick={runSimulation}>
          {loading ? 'Simulating...' : 'Run Simulation (REST)'}
        </button>
        <button className="btn-secondary" disabled={running || !connected} onClick={() => runPipeline(config)}>
          {running ? 'Streaming...' : 'Run Live Pipeline (WS)'}
        </button>
      </div>

      {summary && (
        <p className="mono mt-3">
          WS complete — target_detected: {String(summary.target_detected)}, detections: {summary.num_detections}
        </p>
      )}
    </main>
  )
}