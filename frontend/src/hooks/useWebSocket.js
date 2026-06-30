'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { getWebSocketUrl } from '@/lib/api'

/**
 * Drives the animated step-by-step pipeline view (the "wow moment" flow):
 * Chirp Generation -> Range FFT -> Doppler FFT -> CFAR -> Micro-Doppler -> Vitals
 *
 * Each WS message updates `steps` keyed by stage index, so the frontend
 * can light up pipeline stage cards live as they complete.
 *
 * Polish note: React Strict Mode (dev only) mounts effects twice, so the
 * first WebSocket is opened and immediately torn down before the real
 * one connects. That throwaway socket's onerror can fire before its
 * onclose, flashing a false "connection failed" message for one render.
 * We guard against this by only surfacing wsError once the cleanup flag
 * confirms this effect instance is still the active one.
 */
export function useWebSocket() {
  const wsRef = useRef(null)
  const isActiveRef = useRef(true)
  const [connected, setConnected] = useState(false)
  const [steps, setSteps] = useState({})
  const [summary, setSummary] = useState(null)
  const [running, setRunning] = useState(false)
  const [wsError, setWsError] = useState(null)

  useEffect(() => {
    isActiveRef.current = true
    const ws = new WebSocket(getWebSocketUrl())
    wsRef.current = ws

    ws.onopen = () => {
      if (isActiveRef.current) setConnected(true)
    }
    ws.onclose = () => {
      if (isActiveRef.current) setConnected(false)
    }
    ws.onerror = () => {
      // Only surface the error if this socket is still live a tick later —
      // filters out the Strict Mode throwaway connection's spurious error.
      setTimeout(() => {
        if (isActiveRef.current && wsRef.current === ws && ws.readyState !== WebSocket.OPEN) {
          setWsError('Connection to radar backend failed.')
        }
      }, 50)
    }

    ws.onmessage = (event) => {
      if (!isActiveRef.current) return
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

    return () => {
      isActiveRef.current = false
      ws.close()
    }
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