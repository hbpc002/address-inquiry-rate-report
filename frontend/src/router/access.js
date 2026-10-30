export const ACCESS_ROUTES = [
  { path: '/', permission: 'dashboard.view' },
  { path: '/checkin-report', permission: 'checkin_report.view' },
  { path: '/workload-report', permission: 'workload_report.view' },
  { path: '/broadband-report', permission: 'broadband_report.view' },
  { path: '/marketing-report', permission: 'marketing_report.view' },
  { path: '/marketing-overall', permission: 'marketing_overall.view' },
  { path: '/reports', permission: 'reports.view' },
  { path: '/schedules', permission: 'schedules.view' },
  { path: '/employees', permission: 'employees.view' },
  { path: '/checkins', permission: 'checkins.view' },
  { path: '/training-records', permission: 'training_records.view' },
  { path: '/workloads', permission: 'workload.view' },
  { path: '/broadband-orders', permission: 'broadband.view' },
  { path: '/marketing-orders', permission: 'marketing.view' },
  { path: '/system', permission: 'system.view' },
  { path: '/users', permission: 'users.view' },
  { path: '/roles', permission: 'roles.view' },
  { path: '/department-groups', permission: 'department_groups.view' },
  { path: '/work-hour-settings', permission: 'work_hour_settings.view' },
  { path: '/salary-settings', permission: 'salary_config.view' },
  { path: '/field-annotations', permission: 'field_annotations.view' },
  { path: '/marketing-settings', permission: 'marketing_settings.view' },
  { path: '/agent', permission: 'agent.use' },
  { path: '/llm-settings', permission: 'agent.config' }
]

export const NO_PERMISSION_PATH = '/no-permission'

export function getLandingPath(userStore) {
  if (!userStore || !userStore.isLoggedIn) return '/login'
  for (const item of ACCESS_ROUTES) {
    if (userStore.hasPermission(item.permission)) return item.path
  }
  return NO_PERMISSION_PATH
}

export function resolveRouteAccess(to, userStore) {
  if (to.path !== '/login' && !userStore.isLoggedIn) {
    return '/login'
  }

  if (to.path === '/login' && userStore.isLoggedIn) {
    return getLandingPath(userStore)
  }

  if (to.path === NO_PERMISSION_PATH) {
    return true
  }

  if (to.meta?.permission && !userStore.hasPermission(to.meta.permission)) {
    const landing = getLandingPath(userStore)
    if (landing === NO_PERMISSION_PATH || to.path === landing) {
      return NO_PERMISSION_PATH
    }
    return landing
  }

  return true
}
