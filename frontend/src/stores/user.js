import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    const res = await api.post('/auth/login', formData)
    token.value = res.data.access_token
    localStorage.setItem('token', res.data.access_token)
    user.value = res.data.user
    return res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  async function fetchCurrentUser() {
    try {
      const res = await api.get('/auth/me')
      user.value = res.data
    } catch (e) {
      logout()
    }
  }

  async function changePassword(oldPassword, newPassword) {
    const res = await api.post('/users/me/change-password', {
      old_password: oldPassword,
      new_password: newPassword
    })
    return res.data
  }

  function hasPermission(permKey) {
    if (!user.value) return false
    if (user.value.role === 'admin') return true
    try {
      const permissions = JSON.parse(user.value.permissions || '{}')
      return permissions[permKey] === true
    } catch {
      return false
    }
  }

  return { token, user, isLoggedIn, login, logout, fetchCurrentUser, changePassword, hasPermission }
})

export { api }