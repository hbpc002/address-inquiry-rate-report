import { describe, it, expect } from 'vitest'
import { PERMISSION_REGISTRY, getAllPermissionKeys } from '@/permissions'

describe('PERMISSION_REGISTRY.agent', () => {
  it('包含智能体分组及使用/配置权限', () => {
    expect(PERMISSION_REGISTRY.agent).toBeDefined()
    expect(PERMISSION_REGISTRY.agent.label).toBe('哟你通通')
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
    expect(PERMISSION_REGISTRY.agent.label).toBe('哟你通通')
  })
})
