'use client'

import Plot from 'react-plotly.js'

export default function MicroDopplerPlot({ cwtPowerDb, timeAxis, frequencyAxisBpm, theme }) {
  const gridColor = theme === 'dark' ? '#2c2c34' : '#e8e5dc'
  const textColor = theme === 'dark' ? '#8a8a92' : '#6b6b66'

  if (!cwtPowerDb || cwtPowerDb.length === 0) {
    return (
      <div className="flex items-center justify-center h-[260px] text-[0.85rem]" style={{ color: 'var(--text-dim)' }}>
        Spectrogram appears once a target is detected.
      </div>
    )
  }

  const colorscale = theme === 'dark'
    ? [[0, '#1a1a20'], [0.4, '#2e3d44'], [0.7, '#3d6b7a'], [1, '#d99a4e']]
    : [[0, '#faf9f5'], [0.4, '#d6e0e3'], [0.7, '#7fa3b3'], [1, '#b8742a']]

  const trace = {
    z: cwtPowerDb, x: timeAxis, y: frequencyAxisBpm, type: 'heatmap',
    colorscale,
    colorbar: { tickfont: { color: textColor, size: 10 }, outlinewidth: 0 },
    hovertemplate: 'Time: %{x:.1f}s<br>Freq: %{y:.0f} BPM<br>Power: %{z:.1f} dB<extra></extra>',
  }

  return (
    <Plot
      data={[trace]}
      layout={{
        autosize: true, height: 260,
        margin: { l: 55, r: 20, t: 10, b: 40 },
        paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
        xaxis: { title: { text: 'Time (s)', font: { color: textColor, size: 11 } }, color: textColor, gridcolor: gridColor, tickfont: { size: 9 } },
        yaxis: { title: { text: 'Freq (BPM)', font: { color: textColor, size: 11 } }, type: 'log', color: textColor, gridcolor: gridColor, tickfont: { size: 9 } },
        font: { family: 'Inter' },
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
    />
  )
}