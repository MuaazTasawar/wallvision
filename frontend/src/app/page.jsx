'use client'

import dynamic from 'next/dynamic'
import { usePipeline } from '@/hooks/usePipeline'
import { useWebSocket } from '@/hooks/useWebSocket'
import ChirpConfig from '@/components/ChirpConfig'
import TargetPanel from '@/components/TargetPanel'
import PipelineSteps from '@/components/PipelineSteps'

// Plotly touches `window` — must be client-only, no SSR
const RangeDopplerMap = dynamic(() => import('@/components/RangeDopplerMap'), { ssr: false })

export default function Home() {
  const { config, updateConfig, result, loading, error, runSimulation } = usePipeline()
  const { connected, steps, summary, running, wsError, runPipeline } = useWebSocket()

  // Prefer the live WS Doppler-FFT step payload if a live run has completed it,
  // otherwise fall back to the last REST simulation result.
  const dopplerStep = steps[2]?.data
  const cfarStep = steps[3]?.data
  const vitalsStep = steps[5]?.data

  const rdMap = dopplerStep?.range_doppler_db ?? result?.range_doppler_db
  const rangeAxis = dopplerStep?.range_axis ?? result?.range_axis
  const velocityAxis = dopplerStep?.velocity_axis ?? result?.velocity_axis
  const detections = cfarStep?.detections ?? result?.detections ?? []
  const breathingRate = vitalsStep?.breathing_rate_bpm ?? result?.breathing_rate_bpm
  const heartRate = vitalsStep?.heart_rate_bpm ?? result?.heart_rate_bpm
  const vitalsDetected = vitalsStep?.vital_signs_detected ?? result?.vital_signs_detected ?? false

  return (
    <main className="min-h-screen px-6 py-8 max-w-[1400px] mx-auto">
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

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-4">
          <ChirpConfig
            config={config}
            onChange={updateConfig}
            onRun={runSimulation}
            onRunLive={() => runPipeline(config)}
            loading={loading}
            running={running}
            wsConnected={connected}
          />
          <PipelineSteps steps={steps} running={running} summary={summary} />
        </div>

        <div className="col-span-12 lg:col-span-9 flex flex-col gap-4">
          <div className="panel">
            <div className="panel-header">
              <span className={`status-dot ${running ? 'processing' : 'idle'}`} /> Range-Doppler Map
            </div>
            {(error || wsError) && (
              <p className="mono mb-3" style={{ color: 'var(--danger)' }}>
                {error || wsError}
              </p>
            )}
            <RangeDopplerMap
              rangeAxis={rangeAxis}
              velocityAxis={velocityAxis}
              rdMap={rdMap}
              detections={detections}
            />
          </div>

          <TargetPanel
            detections={detections}
            breathingRate={breathingRate}
            heartRate={heartRate}
            vitalsDetected={vitalsDetected}
          />
        </div>
      </div>
    </main>
  )
}