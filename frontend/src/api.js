import axios from 'axios'

const API_BASE = 'https://neuralwatch-api.onrender.com'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Auto-attach token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('nw_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('nw_token')
      localStorage.removeItem('nw_tenant')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth
export const login = (email, password) =>
  api.post('/api/auth/login', { email, password })

export const register = (name, email, password) =>
  api.post('/api/auth/register', { name, email, password })

export const getMe = () =>
  api.get('/api/auth/me')

// Cameras
export const getCameras = () =>
  api.get('/api/cameras')

export const addCamera = (data) =>
  api.post('/api/cameras', data)

export const deleteCamera = (id) =>
  api.delete(`/api/cameras/${id}`)

export const getCameraHealth = (id) =>
  api.get(`/api/cameras/${id}/health`)

// Motion & Alerts
export const getMotionEvents = (cameraId) =>
  api.get(`/api/cameras/${cameraId}/motion`)

export const getAlerts = () =>
  api.get('/api/alerts')

export const dismissAlert = (id) =>
  api.post(`/api/alerts/${id}/dismiss`)

export const confirmAlert = (id) =>
  api.post(`/api/alerts/${id}/confirm`)

// Relay
export const getRelays = () =>
  api.get('/api/relay')

export default api
