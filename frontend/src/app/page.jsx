'use client'

import dynamic from 'next/dynamic'
import { usePipeline } from '@/hooks/usePipeline'
import { useWebSocket } from '@/hooks/useWebSocket'
import ChirpConfig from '@/components/ChirpConfig'
import TargetPanel from '@/components/TargetPanel'
import PipelineSteps from '@/components/PipelineSteps'
import VitalSignsPanel from '@/components/VitalSignsPanel'
import DatasetUploader from '@/components/DatasetUploader'

// Plotly touches `window` — must be client-only, no SSR
const RangeDopplerMap = dynamic(() => import('@/components/RangeDopplerMap'), { ssr: false })
const MicroDopplerPlot = dynamic(() => import('@/components/MicroDopplerPlot'), { ssr: false })

export default function Home() {
  const { config, updateConfig, result, loading, error, runSimulation, runUpload } = usePipeline()
  const { connected, steps, summary, running, wsError, runPipeline } = useWebSocket()

  const dopplerStep = steps[2]?.data
  const cfarStep = steps[3]?.data
  const cwtStep = steps[4]?.data
  const vitalsStep = steps[5]?.data

  const rdMap = dopplerStep?.range_doppler_db ?? result?.range_doppler_db
  const rangeAxis = dopplerStep?.range_axis ?? result?.range_axis
  const velocityAxis = dopplerStep?.velocity_axis ?? result?.velocity_axis
  const detections = cfarStep?.detections ?? result?.detections ?? []
  const breathingRate = vitalsStep?.breathing_rate_bpm ?? result?.breathing_rate_bpm
  const heartRate = vitalsStep?.heart_rate_bpm ?? result?.heart_rate_bpm
  const vitalsDetected = vitalsStep?.vital_signs_detected ?? result?.vital_signs_detected ?? false
  const phaseSignal = vitalsStep?.phase_signal ?? result?.phase_signal
  const breathingSignal = vitalsStep?.breathing_signal ?? result?.breathing_signal
  const cwtPowerDb = cwtStep?.cwt_power_db ?? result?.cwt_power_db
  const cwtTimeAxis = cwtStep?.time_axis ?? result?.cwt_time_axis
  const cwtFreqAxis = cwtStep?.frequency_axis_bpm ?? result?.cwt_frequency_axis

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
          <DatasetUploader onUpload={runUpload} loading={loading} />
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

          <div className="panel">
            <div className="panel-header">
              <span className={`status-dot ${vitalsDetected ? 'detected' : 'idle'}`} /> Micro-Doppler Spectrogram
            </div>
            <MicroDopplerPlot
              cwtPowerDb={cwtPowerDb}
              timeAxis={cwtTimeAxis}
              frequencyAxisBpm={cwtFreqAxis}
            />
          </div>

          <VitalSignsPanel phaseSignal={phaseSignal} breathingSignal={breathingSignal} />
        </div>
      </div>
    </main>
  )
}