'use client'

import { useState, useRef } from 'react'

/**
 * Drag-drop uploader for raw TI DCA1000 .bin captures. The user must
 * declare num_chirps/num_samples since the .bin file has no header
 * describing its own shape (matches the backend's validate_capture_size
 * pre-flight check).
 */
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
    <div className="panel">
      <div className="panel-header">
        <span className="status-dot idle" /> TI mmWave Dataset Upload
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className="border border-dashed rounded-sm p-6 text-center cursor-pointer transition-colors"
        style={{
          borderColor: dragOver ? 'var(--phosphor)' : 'var(--border)',
          background: dragOver ? 'var(--phosphor-glow)' : 'transparent',
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".bin"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <p className="mono">
          {file ? file.name : 'Drop a DCA1000 .bin capture here, or click to browse'}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 mt-4">
        <div>
          <div className="mono mb-1">Num Chirps</div>
          <input
            type="number"
            value={numChirps}
            onChange={(e) => setNumChirps(parseInt(e.target.value) || 0)}
            className="w-full bg-transparent border border-scope-border rounded-sm px-2 py-1 mono text-scope-text"
          />
        </div>
        <div>
          <div className="mono mb-1">Num Samples</div>
          <input
            type="number"
            value={numSamples}
            onChange={(e) => setNumSamples(parseInt(e.target.value) || 0)}
            className="w-full bg-transparent border border-scope-border rounded-sm px-2 py-1 mono text-scope-text"
          />
        </div>
      </div>

      <button
        className="btn-primary w-full mt-4"
        disabled={!file || loading}
        onClick={handleSubmit}
      >
        {loading ? 'Processing capture...' : 'Process Dataset'}
      </button>
    </div>
  )
}