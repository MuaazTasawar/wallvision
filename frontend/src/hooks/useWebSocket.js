'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { getWebSocketUrl } from '@/lib/api'

/**
 * Drives the animated step-by-step pipeline view (the "wow moment" flow):
 * Chirp Generation -> Range FFT -> Doppler FFT -> CFAR -> Micro-Doppler -> Vitals
 *
 * Each WS message updates `steps` keyed by stage index, so the frontend
 * can light up pipeline stage cards live as they complete.
 */
export function useWebSocket() {
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const [steps, setSteps] = useState({})
  const [summary, setSummary] = useState(null)
  const [running, setRunning] = useState(false)
  const [wsError, setWsError] = useState(null)

  useEffect(() => {
    const ws = new WebSocket(getWebSocketUrl())
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setWsError('Connection to radar backend failed.')

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)

      if (msg.type === 'step') {
        setSteps((prev) => ({ ...prev, [msg.index]: { name: msg.name, data: msg.data } }))
      } else if (msg.type === 'complete') {
        setSummary(msg.summary)
        setRunning(false)
      } else if (msg.type === 'error') {
        setWsError(msg.message)
        setRunning(false)
      }
    }

    return () => ws.close()
  }, [])

  const runPipeline = useCallback((config) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setWsError('WebSocket not connected.')
      return
    }
    setSteps({})
    setSummary(null)
    setWsError(null)
    setRunning(true)
    wsRef.current.send(JSON.stringify(config))
  }, [])

  return { connected, steps, summary, running, wsError, runPipeline }
}