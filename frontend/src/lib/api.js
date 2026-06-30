import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

export async function getPipelineSteps() {
  const res = await client.get('/api/pipeline-steps')
  return res.data
}

export async function simulateFrame(config) {
  const res = await client.post('/api/simulate', config)
  return res.data
}

export async function uploadDataset(file, config) {
  const formData = new FormData()
  formData.append('file', file)
  Object.entries(config).forEach(([key, value]) => {
    formData.append(key, value)
  })

  const res = await axios.post(`${API_BASE}/api/upload-dataset`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export function getWebSocketUrl() {
  const wsBase = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://')
  return `${wsBase}/ws/radar-stream`
}

export const DEFAULT_CONFIG = {
  bandwidth_ghz: 1.0,
  center_freq_ghz: 77.0,
  chirp_duration_us: 64.0,
  num_chirps: 128,
  num_samples: 256,
  sample_rate_mhz: 4.0,
  snr_db: 20.0,
  target_range_m: 4.0,
  target_velocity_mps: 0.0,
  breathing_rate_bpm: 15.0,
  breathing_amplitude_mm: 2.0,
  enable_heartbeat: true,
  window_type: 'hann',
  cfar_guard_cells: 2,
  cfar_training_cells: 8,
  cfar_pfa: 0.0001,
}