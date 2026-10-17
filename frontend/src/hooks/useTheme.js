import { useEffect, useState } from 'react'

export function useTheme() {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('quantpilot_theme')
    return saved ? saved === 'dark' : true
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode)
    document.documentElement.classList.toggle('light', !isDarkMode)
    localStorage.setItem('quantpilot_theme', isDarkMode ? 'dark' : 'light')
  }, [isDarkMode])

  return {
    isDarkMode,
    toggleTheme: () => setIsDarkMode((current) => !current),
  }
}
