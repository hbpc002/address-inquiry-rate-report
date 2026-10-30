import { describe, it, expect } from 'vitest'
import {
  ACCESS_ROUTES,
  NO_PERMISSION_PATH,
  getLandingPath,
  resolveRouteAccess
} from '../src/router/access'

function createUserStore(permissions = [], isLoggedIn = true) {
  const allowed = new Set(permissions)
  return {
    isLoggedIn,
    user: isLoggedIn ? {} : null,
    hasPermission: key => allowed.has(key)
  }
}

describe('router access - landing path', () => {
  it('prefers the dashboard when the user can view it', () => {
    const store = createUserStore(['dashboard.view', 'employees.view'])
    expect(getLandingPath(store)).toBe('/')
  })

  it('falls back to the first accessible page when dashboard is unavailable', () => {
    const store = createUserStore(['employees.view', 'marketing.view'])
    expect(getLandingPath(store)).toBe('/employees')
  })

  it('uses marketing details when only marketing permissions exist', () => {
    const store = createUserStore(['marketing.view'])
    expect(getLandingPath(store)).toBe('/marketing-orders')
  })

  it('uses the overall marketing report when only that permission exists', () => {
    const store = createUserStore(['marketing_overall.view'])
    expect(getLandingPath(store)).toBe('/marketing-overall')
  })

  it('returns the no-permission page when the user has no page permissions', () => {
    const store = createUserStore([])
    expect(getLandingPath(store)).toBe(NO_PERMISSION_PATH)
  })

  it('returns login for logged-out users', () => {
    const store = createUserStore([], false)
    expect(getLandingPath(store)).toBe('/login')
  })
})

describe('router access - navigation resolution', () => {
  it('redirects logged-out users to login', () => {
    const store = createUserStore([], false)
    expect(resolveRouteAccess({ path: '/employees' }, store)).toBe('/login')
  })

  it('redirects logged-in users away from login to their landing page', () => {
    const store = createUserStore(['employees.view'])
    expect(resolveRouteAccess({ path: '/login' }, store)).toBe('/employees')
  })

  it('allows the no-permission page without looping', () => {
    const store = createUserStore([])
    expect(resolveRouteAccess({ path: NO_PERMISSION_PATH }, store)).toBe(true)
  })

  it('redirects an unauthorized dashboard to the first accessible page', () => {
    const store = createUserStore(['employees.view'])
    const to = { path: '/', meta: { permission: 'dashboard.view' } }
    expect(resolveRouteAccess(to, store)).toBe('/employees')
  })

  it('redirects an unauthorized page to another accessible page', () => {
    const store = createUserStore(['marketing.view'])
    const to = { path: '/employees', meta: { permission: 'employees.view' } }
    expect(resolveRouteAccess(to, store)).toBe('/marketing-orders')
  })

  it('sends users with no permissions to the no-permission page', () => {
    const store = createUserStore([])
    const to = { path: '/', meta: { permission: 'dashboard.view' } }
    expect(resolveRouteAccess(to, store)).toBe(NO_PERMISSION_PATH)
  })

  it('allows routes whose permission is granted', () => {
    const store = createUserStore(['employees.view'])
    const to = { path: '/employees', meta: { permission: 'employees.view' } }
    expect(resolveRouteAccess(to, store)).toBe(true)
  })

  it('allows routes without a permission requirement', () => {
    const store = createUserStore([])
    expect(resolveRouteAccess({ path: '/unknown' }, store)).toBe(true)
  })
})

describe('router access - route registry', () => {
  it('covers every main page and uses unique paths', () => {
    const paths = ACCESS_ROUTES.map(item => item.path)
    expect(new Set(paths).size).toBe(paths.length)
    expect(paths).toContain('/')
    expect(paths).toContain('/employees')
    expect(paths).toContain('/marketing-orders')
    expect(paths).toContain('/department-groups')
    expect(paths).toContain('/llm-settings')
  })
})
