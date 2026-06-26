import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  paramsSerializer: {
    indexes: null
  }
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

  const isSystem = computed(() => user.value?.is_system === true)

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
    if (user.value.is_system === true) return true
    try {
      const permissions = JSON.parse(user.value.permissions || '{}')
      return permissions[permKey] === true
    } catch {
      return false
    }
  }

  function hasAnyPermission(permKeys) {
    return permKeys.some(k => hasPermission(k))
  }

  function canEdit() {
    return hasAnyPermission([
      'schedules.create', 'schedules.edit', 'schedules.delete',
      'employees.create', 'employees.edit', 'employees.delete',
      'checkins.delete',
      'shift_types.create', 'shift_types.edit', 'shift_types.delete',
      'work_hour_settings.create', 'work_hour_settings.edit', 'work_hour_settings.delete',
    ])
  }

  function canView(pageKey) {
    return hasPermission(`${pageKey}.view`)
  }

  return { token, user, isLoggedIn, isSystem, login, logout, fetchCurrentUser, changePassword, hasPermission, hasAnyPermission, canEdit, canView }
})

export { api }