import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
})

// Injecter le JWT dans chaque requête si disponible
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Rediriger vers /login si le token est expiré ou invalide
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)
