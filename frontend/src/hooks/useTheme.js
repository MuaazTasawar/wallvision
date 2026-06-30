'use client'

import { useState, useEffect, useCallback } from 'react'

/**
 * Light/dark theme toggle. Persists choice to localStorage and
 * toggles the `dark` class on <html> (Tailwind darkMode: 'class').
 * Defaults to the user's OS preference on first load.
 */
export function useTheme() {
  const [theme, setTheme] = useState('light')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const stored = window.localStorage.getItem('wallvision-theme')
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const initial = stored || (systemDark ? 'dark' : 'light')
    setTheme(initial)
    document.documentElement.classList.toggle('dark', initial === 'dark')
    setMounted(true)
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === 'light' ? 'dark' : 'light'
      document.documentElement.classList.toggle('dark', next === 'dark')
      window.localStorage.setItem('wallvision-theme', next)
      return next
    })
  }, [])

  return { theme, toggleTheme, mounted }
}