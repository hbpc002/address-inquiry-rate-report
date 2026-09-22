import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'

const root = path.dirname(fileURLToPath(import.meta.url))
const systemVue = readFileSync(path.join(root, '../src/views/System.vue'), 'utf8')
const agentSettingsVue = readFileSync(path.join(root, '../src/views/AgentSettings.vue'), 'utf8')
const agentChatVue = readFileSync(path.join(root, '../src/views/AgentChat.vue'), 'utf8')

describe('System.vue 智能体配置页签', () => {
  it('外层页签标题为「智能体配置」', () => {
    expect(systemVue).toContain('label="智能体配置"')
    expect(systemVue).not.toContain('label="模型配置"')
  })

  it('内含「模型提供商」与「智能体设置」子页签', () => {
    expect(systemVue).toContain('label="模型提供商"')
    expect(systemVue).toContain('label="智能体设置"')
    expect(systemVue).toContain('agentSubTab')
    expect(systemVue).toContain('AgentSettings')
    expect(systemVue).toContain('LLMSettings')
  })

  it('仍使用 agent.config 权限', () => {
    expect(systemVue).toContain("hasPermission('agent.config')")
  })
})

describe('AgentSettings.vue', () => {
  it('包含系统提示词、快捷问题、运行参数', () => {
    expect(agentSettingsVue).toContain('系统提示词')
    expect(agentSettingsVue).toContain('快捷问题建议')
    expect(agentSettingsVue).toContain('运行参数')
    expect(agentSettingsVue).toContain('max_iterations')
    expect(agentSettingsVue).toContain('max_history_messages')
    expect(agentSettingsVue).toContain('consecutive_run_sql_failures')
    expect(agentSettingsVue).toContain('{current_date}')
  })

  it('调用保存与恢复默认接口', () => {
    expect(agentSettingsVue).toContain("'/agent-settings'")
    expect(agentSettingsVue).toContain('恢复默认')
  })
})

describe('AgentChat.vue 快捷问题动态加载', () => {
  it('从 /agent-settings 加载 suggestions 并保留默认回退', () => {
    expect(agentChatVue).toContain("'/agent-settings'")
    expect(agentChatVue).toContain('DEFAULT_SUGGESTIONS')
    expect(agentChatVue).toContain('loadSuggestions')
  })
})
