import { describe, it, expect } from 'vitest'
import { PERMISSION_REGISTRY, getAllPermissionKeys } from '@/permissions'

describe('PERMISSION_REGISTRY.agent', () => {
  it('包含智能体分组及使用/配置权限', () => {
    expect(PERMISSION_REGISTRY.agent).toBeDefined()
    expect(PERMISSION_REGISTRY.agent.label).toBe('智能助手')
    expect(PERMISSION_REGISTRY.agent.permissions.use).toBe('使用对话')
    expect(PERMISSION_REGISTRY.agent.permissions.config).toBe('模型与界面配置')
  })

  it('getAllPermissionKeys 包含 agent.use 与 agent.config', () => {
    const keys = getAllPermissionKeys()
    expect(keys).toContain('agent.use')
    expect(keys).toContain('agent.config')
  })
})

describe('界面名称配置权限', () => {
  it('system.config 存在于注册表', () => {
    expect(PERMISSION_REGISTRY.system.permissions.config).toBe('界面名称配置')
    expect(getAllPermissionKeys()).toContain('system.config')
  })
})

describe('菜单名称重命名', () => {
  it('checkin_report 标签为 排班调度', () => {
    expect(PERMISSION_REGISTRY.checkin_report.label).toBe('排班调度')
  })
  it('workload_report 标签为 团队管理', () => {
    expect(PERMISSION_REGISTRY.workload_report.label).toBe('团队管理')
  })
  it('agent 标签为 哟你通通', () => {
    expect(PERMISSION_REGISTRY.agent.label).toBe('智能助手')
  })
})


describe('营销统计权限', () => {
  it('包含营销明细、营销统计、总体营销与营销设置权限', () => {
    expect(PERMISSION_REGISTRY.marketing.permissions.view).toBe('查看')
    expect(PERMISSION_REGISTRY.marketing.permissions.upload).toBe('导入')
    expect(PERMISSION_REGISTRY.marketing.permissions.delete).toBe('删除')
    expect(PERMISSION_REGISTRY.marketing_report.permissions.export).toBe('导出')
    expect(PERMISSION_REGISTRY.marketing_overall.permissions.export).toBe('导出')
    expect(PERMISSION_REGISTRY.marketing_settings.permissions.edit).toBe('编辑')
    const keys = getAllPermissionKeys()
    for (const key of ['marketing.view', 'marketing.upload', 'marketing.delete', 'marketing_report.view', 'marketing_report.export', 'marketing_overall.view', 'marketing_overall.export', 'marketing_settings.view', 'marketing_settings.edit']) {
      expect(keys).toContain(key)
    }
  })
})


describe('首页与数据范围权限', () => {
  it('包含首页查看权限', () => {
    expect(PERMISSION_REGISTRY.dashboard.permissions.view).toBe('查看')
    expect(getAllPermissionKeys()).toContain('dashboard.view')
  })
})
