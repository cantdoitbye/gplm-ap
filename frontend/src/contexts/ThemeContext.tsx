import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

type ThemeMode = 'light' | 'dark' | 'system'
type ResolvedTheme = 'light' | 'dark'

interface ThemeContextType {
  themeMode: ThemeMode
  resolvedTheme: ResolvedTheme
  setThemeMode: (mode: ThemeMode) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

const THEME_STORAGE_KEY = 'aikosh5-theme'

function getInitialThemeMode(): ThemeMode {
  if (typeof window === 'undefined') return 'system'
  
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode | null
  if (storedTheme === 'light' || storedTheme === 'dark' || storedTheme === 'system') {
    return storedTheme
  }
  
  return 'system'
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(getInitialThemeMode)
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => {
    const mode = getInitialThemeMode()
    return mode === 'system' ? getSystemTheme() : mode
  })

  useEffect(() => {
    const root = document.documentElement
    
    if (resolvedTheme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    
    localStorage.setItem(THEME_STORAGE_KEY, themeMode)
  }, [resolvedTheme, themeMode])

  useEffect(() => {
    if (themeMode !== 'system') {
      setResolvedTheme(themeMode)
      return
    }

    setResolvedTheme(getSystemTheme())

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const handleChange = (e: MediaQueryListEvent) => {
      if (themeMode === 'system') {
        setResolvedTheme(e.matches ? 'dark' : 'light')
      }
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [themeMode])

  const setThemeMode = (mode: ThemeMode) => {
    setThemeModeState(mode)
  }

  const toggleTheme = () => {
    setThemeModeState(prev => {
      if (prev === 'system') {
        return resolvedTheme === 'dark' ? 'light' : 'dark'
      }
      return prev === 'light' ? 'dark' : 'light'
    })
  }

  return (
    <ThemeContext.Provider value={{ themeMode, resolvedTheme, setThemeMode, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

export { ThemeContext }
export type { ThemeMode, ResolvedTheme }
