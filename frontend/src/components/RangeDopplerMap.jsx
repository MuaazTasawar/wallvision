'use client'

import Plot from 'react-plotly.js'

export default function RangeDopplerMap({ rangeAxis, velocityAxis, rdMap, detections = [], theme }) {
  const gridColor = theme === 'dark' ? '#2c2c34' : '#e8e5dc'
  const textColor = theme === 'dark' ? '#8a8a92' : '#6b6b66'

  if (!rdMap || rdMap.length === 0) {
    return (
      <div className="flex items-center justify-center h-[380px] text-[0.85rem]" style={{ color: 'var(--text-dim)' }}>
        Run a simulation to render the Range-Doppler map.
      </div>
    )
  }

  const colorscale = theme === 'dark'
    ? [[0, '#1a1a20'], [0.4, '#2c3a2c'], [0.7, '#4f7a45'], [1, '#6fb863']]
    : [[0, '#faf9f5'], [0.4, '#dde6da'], [0.7, '#8fb583'], [1, '#3d6b35']]

  const heatmapTrace = {
    z: rdMap, x: rangeAxis, y: velocityAxis, type: 'heatmap',
    colorscale,
    colorbar: { tickfont: { color: textColor, family: 'Inter', size: 10 }, outlinewidth: 0 },
    hovertemplate: 'Range: %{x:.2f} m<br>Velocity: %{y:.2f} m/s<br>Power: %{z:.1f} dB<extra></extra>',
  }

  const markerTrace = {
    x: detections.map((d) => d.range_m),
    y: detections.map((d) => d.velocity_mps),
    mode: 'markers+text', type: 'scatter',
    marker: { size: 14, color: 'rgba(0,0,0,0)', line: { color: '#b8742a', width: 2 } },
    text: detections.map((d) => `${d.snr_db.toFixed(0)} dB`),
    textposition: 'top center',
    textfont: { color: '#b8742a', family: 'Inter', size: 11, weight: 600 },
    hovertemplate: 'TARGET<br>Range: %{x:.2f} m<br>Velocity: %{y:.2f} m/s<extra></extra>',
    showlegend: false,
  }

  return (
    <Plot
      data={[heatmapTrace, markerTrace]}
      layout={{
        autosize: true, height: 380,
        margin: { l: 55, r: 20, t: 10, b: 45 },
        paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
        xaxis: { title: { text: 'Range (m)', font: { color: textColor, size: 11 } }, color: textColor, gridcolor: gridColor, tickfont: { size: 9 } },
        yaxis: { title: { text: 'Velocity (m/s)', font: { color: textColor, size: 11 } }, color: textColor, gridcolor: gridColor, tickfont: { size: 9 } },
        font: { family: 'Inter' },
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
    />
  )
}