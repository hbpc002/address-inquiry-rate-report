import { describe, it, expect } from 'vitest'
import { PERMISSION_REGISTRY, getAllPermissionKeys } from '@/permissions'

describe('PERMISSION_REGISTRY.agent', () => {
  it('包含智能体分组及使用/配置权限', () => {
    expect(PERMISSION_REGISTRY.agent).toBeDefined()
    expect(PERMISSION_REGISTRY.agent.label).toBe('智能体')
    expect(PERMISSION_REGISTRY.agent.permissions.use).toBe('使用对话')
    expect(PERMISSION_REGISTRY.agent.permissions.config).toBe('模型与界面配置')
  })

  it('getAllPermissionKeys 包含 agent.use 与 agent.config', () => {
    const keys = getAllPermissionKeys()
    expect(keys).toContain('agent.use')
    expect(keys).toContain('agent.config')
  })
})
