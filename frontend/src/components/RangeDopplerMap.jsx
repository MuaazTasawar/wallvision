'use client'

import Plot from 'react-plotly.js'

/**
 * 2D heatmap of the Range-Doppler magnitude map (dB), with CFAR
 * detection markers overlaid as scatter points at their (range, velocity)
 * coordinates.
 */
export default function RangeDopplerMap({ rangeAxis, velocityAxis, rdMap, detections = [] }) {
  if (!rdMap || rdMap.length === 0) {
    return (
      <div className="flex items-center justify-center h-[420px] mono text-scope-text-faint">
        Run a simulation to render the Range-Doppler map.
      </div>
    )
  }

  const heatmapTrace = {
    z: rdMap,
    x: rangeAxis,
    y: velocityAxis,
    type: 'heatmap',
    colorscale: [
      [0, '#0a0e0a'],
      [0.3, '#1a2a12'],
      [0.55, '#3d4d2a'],
      [0.75, '#6b9438'],
      [1, '#8fd13f'],
    ],
    colorbar: {
      title: { text: 'dB', font: { color: '#6f7a64', family: 'IBM Plex Mono', size: 10 } },
      tickfont: { color: '#6f7a64', family: 'IBM Plex Mono', size: 9 },
      outlinewidth: 0,
    },
    hovertemplate: 'Range: %{x:.2f} m<br>Velocity: %{y:.2f} m/s<br>Power: %{z:.1f} dB<extra></extra>',
  }

  const markerTrace = {
    x: detections.map((d) => d.range_m),
    y: detections.map((d) => d.velocity_mps),
    mode: 'markers+text',
    type: 'scatter',
    marker: { size: 13, color: 'rgba(0,0,0,0)', line: { color: '#e8973a', width: 2 }, symbol: 'circle' },
    text: detections.map((d) => `${d.snr_db.toFixed(0)} dB`),
    textposition: 'top center',
    textfont: { color: '#e8973a', family: 'IBM Plex Mono', size: 10 },
    hovertemplate: 'TARGET<br>Range: %{x:.2f} m<br>Velocity: %{y:.2f} m/s<extra></extra>',
    showlegend: false,
  }

  return (
    <Plot
      data={[heatmapTrace, markerTrace]}
      layout={{
        autosize: true,
        height: 420,
        margin: { l: 55, r: 20, t: 10, b: 45 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        xaxis: {
          title: { text: 'Range (m)', font: { color: '#6f7a64', family: 'IBM Plex Mono', size: 10 } },
          color: '#6f7a64',
          gridcolor: '#2a3326',
          tickfont: { family: 'IBM Plex Mono', size: 9 },
        },
        yaxis: {
          title: { text: 'Velocity (m/s)', font: { color: '#6f7a64', family: 'IBM Plex Mono', size: 10 } },
          color: '#6f7a64',
          gridcolor: '#2a3326',
          tickfont: { family: 'IBM Plex Mono', size: 9 },
        },
        font: { family: 'IBM Plex Mono' },
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
    />
  )
}