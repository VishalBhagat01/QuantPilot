import { useCallback, useState } from 'react'
import { apiUrl } from '../lib/apiClient'
import { getAuthHeaders } from '../authApi'

export function useTradingScan() {
  const [scanResult, setScanResult] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [scanStep, setScanStep] = useState(0)
  const [error, setError] = useState(null)

  const scanSymbol = useCallback(async (symbol) => {
    const cleanSymbol = symbol.trim().toUpperCase()
    if (!cleanSymbol) return null

    setScanning(true)
    setScanStep(1)
    setScanResult(null)
    setError(null)
    const stepTimer1 = setTimeout(() => setScanStep(2), 500)
    const stepTimer2 = setTimeout(() => setScanStep(3), 1100)

    try {
      const response = await fetch(apiUrl(`/trading/scan/${cleanSymbol}`), {
        method: 'POST',
        headers: getAuthHeaders(),
      })
      if (!response.ok) throw new Error(`Scan failed: ${response.statusText}`)
      const result = await response.json()
      setScanResult(result)
      return result
    } catch (scanError) {
      console.error('[useTradingScan] Scan failed:', scanError)
      setError(`Scan failed for ${cleanSymbol}: ${scanError.message}`)
      return null
    } finally {
      clearTimeout(stepTimer1)
      clearTimeout(stepTimer2)
      setScanning(false)
      setScanStep(0)
    }
  }, [])

  return { scanResult, scanning, scanStep, error, scanSymbol }
}
