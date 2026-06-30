'use client'

import { useState, useCallback } from 'react'
import { simulateFrame, uploadDataset, DEFAULT_CONFIG } from '@/lib/api'

/**
 * Manages radar configuration state and triggers REST-based pipeline runs.
 * Used for the "static" run mode (single simulate / upload call) — the
 * step-by-step animated mode uses useWebSocket instead.
 */
export function usePipeline() {
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const updateConfig = useCallback((partial) => {
    setConfig((prev) => ({ ...prev, ...partial }))
  }, [])

  const runSimulation = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await simulateFrame(config)
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }, [config])

  const runUpload = useCallback(async (file) => {
    setLoading(true)
    setError(null)
    try {
      const data = await uploadDataset(file, config)
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Dataset processing failed')
    } finally {
      setLoading(false)
    }
  }, [config])

  return {
    config,
    updateConfig,
    result,
    loading,
    error,
    runSimulation,
    runUpload,
  }
}