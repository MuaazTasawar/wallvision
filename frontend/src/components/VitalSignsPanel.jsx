'use client'

import Plot from 'react-plotly.js'

/**
 * Two stacked traces: the raw unwrapped phase signal (chest motion proxy)
 * and the bandpass-filtered breathing waveform extracted from it — shows
 * the "before/after" of the breathing-band filter visually.
 */
export default function VitalSignsPanel({ phaseSignal, breathingSignal }) {
  if (!phaseSignal || phaseSignal.length === 0) {
    return (
      <div className="panel">
        <div className="panel-header">
          <span className="status-dot idle" /> Phase Signal
        </div>
        <p className="mono text-scope-text-faint">
          Raw and filtered chest-motion phase signal appears once vitals are detected.
        </p>
      </div>
    )
  }

  const sampleIdx = phaseSignal.map((_, i) => i)

  const rawTrace = {
    x: sampleIdx,
    y: phaseSignal,
    type: 'scatter',
    mode: 'lines',
    line: { color: '#2e3d44', width: 1 },
    name: 'Raw phase',
    hovertemplate: 'Sample %{x}<br>Phase: %{y:.3f} rad<extra></extra>',
  }

  const filteredTrace = {
    x: sampleIdx,
    y: breathingSignal,
    type: 'scatter',
    mode: 'lines',
    line: { color: '#8fd13f', width: 1.8 },
    name: 'Breathing band',
    hovertemplate: 'Sample %{x}<br>Phase: %{y:.3f} rad<extra></extra>',
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="status-dot detected" /> Phase Signal — Raw vs. Breathing-Filtered
      </div>
      <Plot
        data={[rawTrace, filteredTrace]}
        layout={{
          autosize: true,
          height: 200,
          margin: { l: 50, r: 20, t: 10, b: 35 },
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          showlegend: true,
          legend: {
            orientation: 'h', y: 1.15,
            font: { color: '#6f7a64', family: 'IBM Plex Mono', size: 9 },
          },
          xaxis: {
            title: { text: 'Frame index', font: { color: '#6f7a64', family: 'IBM Plex Mono', size: 10 } },
            color: '#6f7a64', gridcolor: '#2a3326', tickfont: { family: 'IBM Plex Mono', size: 9 },
          },
          yaxis: {
            title: { text: 'Phase (rad)', font: { color: '#6f7a64', family: 'IBM Plex Mono', size: 10 } },
            color: '#6f7a64', gridcolor: '#2a3326', tickfont: { family: 'IBM Plex Mono', size: 9 },
          },
          font: { family: 'IBM Plex Mono' },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
      />
    </div>
  )
}