'use client'

import { useState, useRef } from 'react'

export default function DatasetUploader({ onUpload, loading }) {
  const [dragOver, setDragOver] = useState(false)
  const [file, setFile] = useState(null)
  const [numChirps, setNumChirps] = useState(128)
  const [numSamples, setNumSamples] = useState(256)
  const inputRef = useRef(null)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) setFile(dropped)
  }

  const handleSubmit = () => {
    if (!file) return
    onUpload(file, { num_chirps: numChirps, num_samples: numSamples })
  }

  return (
    <div className="card">
      <div className="card-title">TI mmWave Dataset</div>
      <div className="card-subtitle">Upload a raw DCA1000 .bin capture</div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className="rounded-xl p-6 text-center cursor-pointer transition-colors text-[0.82rem]"
        style={{
          border: `1.5px dashed ${dragOver ? 'var(--accent)' : 'var(--border)'}`,
          background: dragOver ? 'var(--surface)' : 'transparent',
          color: 'var(--text-dim)',
        }}
      >
        <input ref={inputRef} type="file" accept=".bin" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        {file ? file.name : 'Drop a .bin capture here, or click to browse'}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-4">
        <div>
          <div className="text-[0.72rem] mb-1" style={{ color: 'var(--text-dim)' }}>Num Chirps</div>
          <input type="number" value={numChirps} onChange={(e) => setNumChirps(parseInt(e.target.value) || 0)} className="text-input" />
        </div>
        <div>
          <div className="text-[0.72rem] mb-1" style={{ color: 'var(--text-dim)' }}>Num Samples</div>
          <input type="number" value={numSamples} onChange={(e) => setNumSamples(parseInt(e.target.value) || 0)} className="text-input" />
        </div>
      </div>

      <button className="btn-primary w-full mt-4" disabled={!file || loading} onClick={handleSubmit}>
        {loading ? 'Processing...' : 'Process Dataset'}
      </button>
    </div>
  )
}