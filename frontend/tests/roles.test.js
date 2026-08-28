import { describe, it, expect } from 'vitest'
import { PERMISSION_REGISTRY, getAllPermissionKeys } from '../src/permissions'

describe('Roles page - permission registry', () => {
  it('should have 15 permission groups including salary_config and agent', () => {
    const groups = Object.keys(PERMISSION_REGISTRY)
    expect(groups).toContain('salary_config')
    expect(groups).toContain('agent')
    expect(groups.length).toBe(16)
  })

  it('getAllPermissionKeys should include salary_config.view', () => {
    const keys = getAllPermissionKeys()
    expect(keys).toContain('salary_config.view')
  })

  it('PERMISSION_REGISTRY should have correct labels for workload pages', () => {
    expect(PERMISSION_REGISTRY.workload.label).toBe('工作量详单')
    expect(PERMISSION_REGISTRY.workload_report.label).toBe('工作量报表')
    expect(PERMISSION_REGISTRY.salary_config.label).toBe('绩效配置')
  })

  it('salary_config should only have view permission', () => {
    const perms = Object.keys(PERMISSION_REGISTRY.salary_config.permissions)
    expect(perms).toEqual(['view'])
  })
})
