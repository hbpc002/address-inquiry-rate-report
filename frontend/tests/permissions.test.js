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
})
