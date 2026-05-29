export const PERMISSION_REGISTRY = {
  employees: {
    label: '员工管理',
    permissions: {
      view: '查看',
      create: '新增',
      edit: '编辑',
      delete: '删除',
      upload: '导入',
    },
  },
  schedules: {
    label: '排班管理',
    permissions: {
      view: '查看',
      create: '新增',
      edit: '编辑',
      delete: '删除',
      upload: '导入',
    },
  },
  checkins: {
    label: '签到记录',
    permissions: {
      view: '查看',
      delete: '删除',
      upload: '导入',
    },
  },
  checkin_report: {
    label: '签入签出报表',
    permissions: {
      view: '查看',
    },
  },
  reports: {
    label: '考勤报表',
    permissions: {
      view: '查看',
    },
  },
  shift_types: {
    label: '班次管理',
    permissions: {
      view: '查看',
      create: '新增',
      edit: '编辑',
      delete: '删除',
    },
  },
  work_hour_settings: {
    label: '工时预警设置',
    permissions: {
      view: '查看',
      create: '新增',
      edit: '编辑',
      delete: '删除',
    },
  },
  system: {
    label: '系统管理',
    permissions: {
      view: '查看',
      clear_data: '清除数据',
    },
  },
  users: {
    label: '用户管理',
    permissions: {
      view: '查看',
      manage: '管理用户',
    },
  },
  roles: {
    label: '角色管理',
    permissions: {
      view: '查看',
      manage: '管理角色',
    },
  },
}

export function getAllPermissionKeys() {
  const keys = []
  for (const [page, info] of Object.entries(PERMISSION_REGISTRY)) {
    for (const action of Object.keys(info.permissions)) {
      keys.push(`${page}.${action}`)
    }
  }
  return keys
}

export function permissionLabel(key) {
  const [page, action] = key.split('.')
  const pageInfo = PERMISSION_REGISTRY[page]
  if (!pageInfo) return key
  const actionLabel = pageInfo.permissions[action]
  if (!actionLabel) return key
  return `${pageInfo.label} - ${actionLabel}`
}

export function getDefaultPermissions(roleName) {
  const allKeys = getAllPermissionKeys()
  if (roleName === 'admin') {
    return Object.fromEntries(allKeys.map(k => [k, true]))
  }

  const adminOnlyViews = new Set(['system', 'users', 'roles'])
  const adminOnlyActions = new Set(['clear_data', 'manage'])

  const result = {}
  for (const [page, info] of Object.entries(PERMISSION_REGISTRY)) {
    for (const action of Object.keys(info.permissions)) {
      if (action === 'view') {
        result[`${page}.${action}`] = !adminOnlyViews.has(page)
      } else if (adminOnlyActions.has(action)) {
        result[`${page}.${action}`] = false
      } else {
        result[`${page}.${action}`] = roleName === 'manager'
      }
    }
  }
  return result
}