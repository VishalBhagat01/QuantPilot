import axios from 'axios'

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})

export function apiUrl(path) {
  return `${API_BASE}${path}`
}
