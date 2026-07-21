export const PERMISSION_REGISTRY = {
    employees: {
    label: '员工管理',
    permissions: {
      view: '查看',
      create: '新增',
      edit: '编辑',
      delete: '删除',
      restore: '恢复',
      upload: '导入',
      export: '导出',
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
      export: '导出',
    },
  },
  workload: {
    label: '工作量详单',
    permissions: {
      view: '查看',
      upload: '导入',
      delete: '删除',
    },
  },
  workload_report: {
    label: '工作量报表',
    permissions: {
      view: '查看',
      export: '导出',
      view_call_salary: '查看接话绩效',
      view_sat_salary: '查看满意度绩效',
      view_total_salary: '查看合计绩效',
      view_gap: '查看话务量差额',
      view_sat_diff: '查看满意度差额',
    },
  },
  reports: {
    label: '考勤报表',
    permissions: {
      view: '查看',
      recalculate: '重算考勤',
      export: '导出报表',
      dashboard_export: '仪表盘导出',
      efficiency_export: '效能监控导出',
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
      changelogs: '管理更新日志',
      export_logs: '导出日志',
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
  salary_config: {
    label: '绩效配置',
    permissions: {
      view: '查看',
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