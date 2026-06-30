'use client'

import Plot from 'react-plotly.js'

/**
 * CWT micro-Doppler spectrogram — time vs frequency (in BPM), power in dB.
 * Breathing (~12-30 BPM) and heartbeat (~48-120 BPM) bands sit at very
 * different frequency rows, so both are visible at once on a log-spaced
 * frequency axis without needing separate plots.
 */
export default function MicroDopplerPlot({ cwtPowerDb, timeAxis, frequencyAxisBpm }) {
  if (!cwtPowerDb || cwtPowerDb.length === 0) {
    return (
      <div className="flex items-center justify-center h-[280px] mono text-scope-text-faint">
        Micro-Doppler spectrogram appears once a target is detected and vitals are extracted.
      </div>
    )
  }

  const trace = {
    z: cwtPowerDb,
    x: timeAxis,
    y: frequencyAxisBpm,
    type: 'heatmap',
    colorscale: [
      [0, '#0a0e0a'],
      [0.35, '#2e3d44'],
      [0.6, '#3d6b7a'],
      [0.8, '#6b8a9e'],
      [1, '#e8973a'],
    ],
    colorbar: {
      title: { text: 'dB', font: { color: '#6f7a64', family: 'IBM Plex Mono', size: 10 } },
      tickfont: { color: '#6f7a64', family: 'IBM Plex Mono', size: 9 },
      outlinewidth: 0,
    },
    hovertemplate: 'Time: %{x:.1f}s<br>Freq: %{y:.0f} BPM<br>Power: %{z:.1f} dB<extra></extra>',
  }

  return (
    <Plot
      data={[trace]}
      layout={{
        autosize: true,
        height: 280,
        margin: { l: 55, r: 20, t: 10, b: 40 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        xaxis: {
          title: { text: 'Time (s)', font: { color: '#6f7a64', family: 'IBM Plex Mono', size: 10 } },
          color: '#6f7a64',
          gridcolor: '#2a3326',
          tickfont: { family: 'IBM Plex Mono', size: 9 },
        },
        yaxis: {
          title: { text: 'Freq (BPM)', font: { color: '#6f7a64', family: 'IBM Plex Mono', size: 10 } },
          type: 'log',
          color: '#6f7a64',
          gridcolor: '#2a3326',
          tickfont: { family: 'IBM Plex Mono', size: 9 },
        },
        font: { family: 'IBM Plex Mono' },
        shapes: [
          // Reference bands: breathing (12-30 BPM) and heartbeat (48-120 BPM)
          {
            type: 'rect', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: 12, y1: 30,
            fillcolor: 'rgba(143,209,63,0.06)', line: { width: 0 },
          },
          {
            type: 'rect', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: 48, y1: 120,
            fillcolor: 'rgba(232,151,58,0.06)', line: { width: 0 },
          },
        ],
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
    />
  )
}