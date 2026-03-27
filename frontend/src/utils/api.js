import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// Auth
export const authAPI = {
  register: d => api.post('/auth/register', d),
  login:    d => api.post('/auth/login', d),
}

// Users
export const usersAPI = {
  me:      ()   => api.get('/users/me'),
  upgrade: tier => api.post('/users/upgrade', { tier }),
}

// Scans
export const scansAPI = {
  scanGithub: fd     => api.post('/scans/github', fd),
  scanUpload: fd     => api.post('/scans/upload', fd),
  scanDast:   fd     => api.post('/scans/dast', fd),
  list:       params => api.get('/scans', { params }),
  get:        id     => api.get(`/scans/${id}`),
  delete:     id     => api.delete(`/scans/${id}`),
}

/**
 * Download a PDF report with JWT auth.
 * Direct <a href> navigation drops the Authorization header → 403.
 * This fetches the PDF as a blob and triggers a real browser download.
 */
export async function downloadReport(scanId, filename) {
  const token = localStorage.getItem('token')
  const resp = await fetch(`/api/scans/${scanId}/report`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!resp.ok) throw new Error(`Download failed (${resp.status})`)
  const blob = await resp.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = filename || `scan_${scanId}_report.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}