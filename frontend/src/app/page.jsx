'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import { usePipeline } from '@/hooks/usePipeline'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useTheme } from '@/hooks/useTheme'
import ThemeToggle from '@/components/ThemeToggle'
import Sidebar from '@/components/Sidebar'
import ChirpConfig from '@/components/ChirpConfig'
import TargetPanel from '@/components/TargetPanel'
import PipelineSteps from '@/components/PipelineSteps'
import VitalSignsPanel from '@/components/VitalSignsPanel'
import DatasetUploader from '@/components/DatasetUploader'

const RangeDopplerMap = dynamic(() => import('@/components/RangeDopplerMap'), { ssr: false })
const MicroDopplerPlot = dynamic(() => import('@/components/MicroDopplerPlot'), { ssr: false })

export default function Home() {
  const { theme, toggleTheme, mounted } = useTheme()
  const [activeNav, setActiveNav] = useState('dashboard')
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

  if (!mounted) return null

  const PAGE_META = {
    dashboard: { title: 'FMCW Radar Console', subtitle: 'Through-wall human detection & vital sign extraction' },
    live: { title: 'Live Pipeline', subtitle: 'Step-by-step DSP stage streaming over WebSocket' },
    dataset: { title: 'Dataset Upload', subtitle: 'Process raw TI mmWave radar captures' },
  }
  const meta = PAGE_META[activeNav]

  return (
    <div className="flex min-h-screen" style={{ background: 'var(--bg)' }}>
      <Sidebar active={activeNav} onSelect={setActiveNav} />

      <main className="flex-1 px-5 lg:px-8 py-6 max-w-[1300px] mx-auto w-full">
        <header className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold">{meta.title}</h1>
            <p className="text-[0.8rem] mt-0.5" style={{ color: 'var(--text-dim)' }}>{meta.subtitle}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="pill">
              <span className={`dot ${connected ? 'on' : 'off'}`} />
              {connected ? 'Connected' : 'Connecting'}
            </span>
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
          </div>
        </header>

        {/* ── DASHBOARD: full radar view ─────────────────────────── */}
        {activeNav === 'dashboard' && (
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-12 lg:col-span-3 flex flex-col gap-4">
              <ChirpConfig
                config={config} onChange={updateConfig}
                onRun={runSimulation} onRunLive={() => runPipeline(config)}
                loading={loading} running={running} wsConnected={connected}
              />
            </div>

            <div className="col-span-12 lg:col-span-9 flex flex-col gap-4">
              <div className="card">
                <div className="card-title">Range-Doppler Map</div>
                <div className="card-subtitle">Live 2D FFT magnitude with CFAR target overlay</div>
                {(error || wsError) && (
                  <p className="text-[0.8rem] mb-3" style={{ color: 'var(--bad)' }}>{error || wsError}</p>
                )}
                <RangeDopplerMap rangeAxis={rangeAxis} velocityAxis={velocityAxis} rdMap={rdMap} detections={detections} theme={theme} />
              </div>

              <TargetPanel detections={detections} breathingRate={breathingRate} heartRate={heartRate} vitalsDetected={vitalsDetected} />

              <div className="card">
                <div className="card-title">Micro-Doppler Spectrogram</div>
                <div className="card-subtitle">CWT time-frequency decomposition of chest motion</div>
                <MicroDopplerPlot cwtPowerDb={cwtPowerDb} timeAxis={cwtTimeAxis} frequencyAxisBpm={cwtFreqAxis} theme={theme} />
              </div>

              <VitalSignsPanel phaseSignal={phaseSignal} breathingSignal={breathingSignal} theme={theme} />
            </div>
          </div>
        )}

        {/* ── LIVE PIPELINE: stage tracker focused view ───────────── */}
        {activeNav === 'live' && (
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
              <ChirpConfig
                config={config} onChange={updateConfig}
                onRun={runSimulation} onRunLive={() => runPipeline(config)}
                loading={loading} running={running} wsConnected={connected}
              />
            </div>
            <div className="col-span-12 lg:col-span-8 flex flex-col gap-4">
              {wsError && <p className="text-[0.8rem]" style={{ color: 'var(--bad)' }}>{wsError}</p>}
              <PipelineSteps steps={steps} running={running} summary={summary} />
              {vitalsDetected && (
                <TargetPanel detections={detections} breathingRate={breathingRate} heartRate={heartRate} vitalsDetected={vitalsDetected} />
              )}
            </div>
          </div>
        )}

        {/* ── DATASET UPLOAD: focused uploader view ───────────────── */}
        {activeNav === 'dataset' && (
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-12 lg:col-span-5">
              <DatasetUploader onUpload={runUpload} loading={loading} />
            </div>
            <div className="col-span-12 lg:col-span-7 flex flex-col gap-4">
              {error && <p className="text-[0.8rem]" style={{ color: 'var(--bad)' }}>{error}</p>}
              <div className="card">
                <div className="card-title">Range-Doppler Map</div>
                <div className="card-subtitle">Processed output from the uploaded capture</div>
                <RangeDopplerMap rangeAxis={rangeAxis} velocityAxis={velocityAxis} rdMap={rdMap} detections={detections} theme={theme} />
              </div>
              <TargetPanel detections={detections} breathingRate={breathingRate} heartRate={heartRate} vitalsDetected={vitalsDetected} />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}