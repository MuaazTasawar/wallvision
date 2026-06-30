'use client'

import Plot from 'react-plotly.js'

export default function VitalSignsPanel({ phaseSignal, breathingSignal, theme }) {
  const gridColor = theme === 'dark' ? '#2c2c34' : '#e8e5dc'
  const textColor = theme === 'dark' ? '#8a8a92' : '#6b6b66'

  if (!phaseSignal || phaseSignal.length === 0) {
    return (
      <div className="card">
        <div className="card-title">Phase Signal</div>
        <p className="text-[0.82rem]" style={{ color: 'var(--text-dim)' }}>
          Raw and filtered chest-motion phase signal appears once vitals are detected.
        </p>
      </div>
    )
  }

  const idx = phaseSignal.map((_, i) => i)
  const rawColor = theme === 'dark' ? '#3d4148' : '#cfcabb'

  return (
    <div className="card">
      <div className="card-title">Phase Signal</div>
      <div className="card-subtitle">Raw chest motion vs. breathing-filtered waveform</div>
      <Plot
        data={[
          { x: idx, y: phaseSignal, type: 'scatter', mode: 'lines', line: { color: rawColor, width: 1 }, name: 'Raw phase' },
          { x: idx, y: breathingSignal, type: 'scatter', mode: 'lines', line: { color: '#3d6b35', width: 2 }, name: 'Breathing band' },
        ]}
        layout={{
          autosize: true, height: 200,
          margin: { l: 50, r: 20, t: 10, b: 35 },
          paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
          showlegend: true,
          legend: { orientation: 'h', y: 1.18, font: { color: textColor, size: 10 } },
          xaxis: { title: { text: 'Frame index', font: { color: textColor, size: 10 } }, color: textColor, gridcolor: gridColor, tickfont: { size: 9 } },
          yaxis: { title: { text: 'Phase (rad)', font: { color: textColor, size: 10 } }, color: textColor, gridcolor: gridColor, tickfont: { size: 9 } },
          font: { family: 'Inter' },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
      />
    </div>
  )
}