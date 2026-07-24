import { describe, it, expect } from 'vitest'
import { PERMISSION_REGISTRY, getAllPermissionKeys, permissionLabel, getDefaultPermissions } from '../src/permissions'

describe('PERMISSION_REGISTRY', () => {
  it('should include salary_config entry', () => {
    expect(PERMISSION_REGISTRY.salary_config).toBeDefined()
    expect(PERMISSION_REGISTRY.salary_config.label).toBe('绩效配置')
    expect(PERMISSION_REGISTRY.salary_config.permissions.view).toBe('查看')
  })

  it('should include workload entry', () => {
    expect(PERMISSION_REGISTRY.workload).toBeDefined()
    expect(PERMISSION_REGISTRY.workload.label).toBe('工作量详单')
  })

  it('should include workload_report entry', () => {
    expect(PERMISSION_REGISTRY.workload_report).toBeDefined()
    expect(PERMISSION_REGISTRY.workload_report.label).toBe('工作量报表')
    expect(PERMISSION_REGISTRY.workload_report.permissions.view_call_salary).toBe('查看接话绩效')
    expect(PERMISSION_REGISTRY.workload_report.permissions.view_sat_salary).toBe('查看满意度绩效')
    expect(PERMISSION_REGISTRY.workload_report.permissions.view_total_salary).toBe('查看合计绩效')
    expect(PERMISSION_REGISTRY.workload_report.permissions.view_gap).toBe('查看话务量差额')
    expect(PERMISSION_REGISTRY.workload_report.permissions.view_sat_diff).toBe('查看满意度差额')
    expect(PERMISSION_REGISTRY.workload_report.permissions.screenshot).toBe('截图导出')
  })

  it('should include reports.recalculate and reports.export', () => {
    expect(PERMISSION_REGISTRY.reports.permissions.recalculate).toBe('重算考勤')
    expect(PERMISSION_REGISTRY.reports.permissions.export).toBe('导出报表')
  })

  it('should include employees.export', () => {
    expect(PERMISSION_REGISTRY.employees.permissions.export).toBe('导出')
  })

  it('should include system.export_logs', () => {
    expect(PERMISSION_REGISTRY.system.permissions.export_logs).toBe('导出日志')
  })
})

describe('getAllPermissionKeys', () => {
  it('should contain salary_config.view', () => {
    const keys = getAllPermissionKeys()
    expect(keys).toContain('salary_config.view')
  })

  it('should contain workload permissions', () => {
    const keys = getAllPermissionKeys()
    expect(keys).toContain('workload.view')
    expect(keys).toContain('workload.upload')
    expect(keys).toContain('workload.delete')
  })

  it('should contain workload_report.view', () => {
    const keys = getAllPermissionKeys()
    expect(keys).toContain('workload_report.view')
  })

  it('should contain new permission keys', () => {
    const keys = getAllPermissionKeys()
    expect(keys).toContain('reports.recalculate')
    expect(keys).toContain('reports.export')
    expect(keys).toContain('employees.export')
    expect(keys).toContain('system.export_logs')
    expect(keys).toContain('workload_report.view_call_salary')
    expect(keys).toContain('workload_report.view_sat_salary')
    expect(keys).toContain('workload_report.view_total_salary')
    expect(keys).toContain('workload_report.view_gap')
    expect(keys).toContain('workload_report.view_sat_diff')
    expect(keys).toContain('workload_report.screenshot')
  })

  it('should return all keys for all pages', () => {
    const keys = getAllPermissionKeys()
    let expectedCount = 0
    for (const info of Object.values(PERMISSION_REGISTRY)) {
      expectedCount += Object.keys(info.permissions).length
    }
    expect(keys.length).toBe(expectedCount)
  })
})

describe('permissionLabel', () => {
  it('should return label for salary_config.view', () => {
    expect(permissionLabel('salary_config.view')).toBe('绩效配置 - 查看')
  })

  it('should return key for unknown permission', () => {
    expect(permissionLabel('unknown.foo')).toBe('unknown.foo')
  })
})

describe('getDefaultPermissions', () => {
  it('should enable all permissions for admin', () => {
    const perms = getDefaultPermissions('admin')
    expect(perms['salary_config.view']).toBe(true)
    expect(perms['workload.view']).toBe(true)
    expect(perms['workload_report.view']).toBe(true)
  })

  it('should enable salary_config.view for manager', () => {
    const perms = getDefaultPermissions('manager')
    expect(perms['salary_config.view']).toBe(true)
  })

  it('should enable salary_config.view for user', () => {
    const perms = getDefaultPermissions('user')
    expect(perms['salary_config.view']).toBe(true)
  })

  it('should enable new report permissions for admin', () => {
    const perms = getDefaultPermissions('admin')
    expect(perms['reports.recalculate']).toBe(true)
    expect(perms['reports.export']).toBe(true)
    expect(perms['employees.export']).toBe(true)
    expect(perms['system.export_logs']).toBe(true)
    expect(perms['workload_report.view_call_salary']).toBe(true)
    expect(perms['workload_report.view_sat_salary']).toBe(true)
    expect(perms['workload_report.view_total_salary']).toBe(true)
    expect(perms['workload_report.view_gap']).toBe(true)
    expect(perms['workload_report.view_sat_diff']).toBe(true)
    expect(perms['workload_report.screenshot']).toBe(true)
  })

  it('should enable new report permissions for manager', () => {
    const perms = getDefaultPermissions('manager')
    expect(perms['reports.recalculate']).toBe(true)
    expect(perms['reports.export']).toBe(true)
    expect(perms['employees.export']).toBe(true)
    expect(perms['workload_report.view_call_salary']).toBe(true)
    expect(perms['workload_report.view_sat_salary']).toBe(true)
    expect(perms['workload_report.view_total_salary']).toBe(true)
    expect(perms['workload_report.view_gap']).toBe(true)
    expect(perms['workload_report.view_sat_diff']).toBe(true)
    expect(perms['workload_report.screenshot']).toBe(true)
  })

  it('should disable new report permissions for user', () => {
    const perms = getDefaultPermissions('user')
    expect(perms['reports.recalculate']).toBe(false)
    expect(perms['reports.export']).toBe(false)
    expect(perms['employees.export']).toBe(false)
    expect(perms['workload_report.view_call_salary']).toBe(false)
    expect(perms['workload_report.view_sat_salary']).toBe(false)
    expect(perms['workload_report.view_total_salary']).toBe(false)
    expect(perms['workload_report.view_gap']).toBe(false)
    expect(perms['workload_report.view_sat_diff']).toBe(false)
    expect(perms['workload_report.screenshot']).toBe(false)
  })
})
