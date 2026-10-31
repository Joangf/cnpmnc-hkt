import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

// Keep in sync with the inline script in index.html, which applies the theme before first paint.
const STORAGE_KEY = 'carebook-theme'
const THEME_COLOR: Record<Theme, string> = { light: '#8C1D4F', dark: '#1A1215' }
const FADE_MS = 320

function storedTheme(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

const systemTheme = (): Theme => (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
const currentTheme = (): Theme => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLOR[theme])
}

/** Switch with one soft cross-fade: the View Transitions API where supported, otherwise a
 * short colour transition on every element. Instant under reduced motion. */
function switchTheme(theme: Theme) {
  const root = document.documentElement
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return applyTheme(theme)
  if (typeof document.startViewTransition === 'function') {
    document.startViewTransition(() => applyTheme(theme))
    return
  }
  root.classList.add('theme-fading')
  applyTheme(theme)
  window.setTimeout(() => root.classList.remove('theme-fading'), FADE_MS + 20)
}

/** The patient's choice wins and is remembered; until they choose, follow the OS setting. */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(currentTheme)

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => {
      if (storedTheme()) return
      switchTheme(systemTheme())
      setThemeState(systemTheme())
    }
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  const toggle = useCallback(() => {
    const next: Theme = currentTheme() === 'dark' ? 'light' : 'dark'
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Private mode or blocked storage: the switch still works for this visit.
    }
    switchTheme(next)
    setThemeState(next)
  }, [])

  return { theme, toggle }
}
