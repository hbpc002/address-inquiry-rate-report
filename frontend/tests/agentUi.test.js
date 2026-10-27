import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'
import AgentUserMessage from '@/components/AgentUserMessage.vue'
import AgentReply from '@/components/AgentReply.vue'
import AgentComposer from '@/components/AgentComposer.vue'

const root = path.dirname(fileURLToPath(import.meta.url))
const agentChatVue = readFileSync(path.join(root, '../src/views/AgentChat.vue'), 'utf8')
const agentLauncherVue = readFileSync(path.join(root, '../src/components/AgentLauncher.vue'), 'utf8')

describe('AgentChat pi-pocket 风格结构', () => {
  it('移除气泡列表并接入新的用户消息、回复和输入组件', () => {
    expect(agentChatVue).not.toContain('BubbleList')
    expect(agentChatVue).not.toContain('<Prompts')
    expect(agentChatVue).toContain('AgentUserMessage')
    expect(agentChatVue).toContain('AgentReply')
    expect(agentChatVue).toContain('AgentComposer')
    expect(agentChatVue).toContain('agent-transcript')
    expect(agentChatVue).toContain('suggestion-grid')
  })

  it('保留快捷问题动态加载与默认回退', () => {
    expect(agentChatVue).toContain("'/agent-settings'")
    expect(agentChatVue).toContain('DEFAULT_SUGGESTIONS')
    expect(agentChatVue).toContain('loadSuggestions')
  })

  it('抽屉改为响应式宽度', () => {
    expect(agentLauncherVue).toContain('drawerSize')
    expect(agentLauncherVue).toContain("'560px'")
    expect(agentLauncherVue).toContain("'100%'")
  })
})

describe('AgentUserMessage', () => {
  it('渲染用户卡片、时间和正文', () => {
    const wrapper = mount(AgentUserMessage, {
      props: {
        message: {
          content: '最近一周谁工时最低',
          createdAt: new Date('2026-10-27T10:42:00').getTime(),
        },
      },
    })
    expect(wrapper.text()).toContain('你')
    expect(wrapper.text()).toContain('最近一周谁工时最低')
    expect(wrapper.find('.user-time').text()).toMatch(/10:42/)
  })
})

describe('AgentReply', () => {
  const timelineStub = {
    name: 'AgentTimeline',
    props: ['steps', 'streaming'],
    template: '<div class="timeline-stub">{{ steps.length }}-{{ streaming }}</div>',
  }
  const markdownStub = {
    name: 'MarkdownMessage',
    props: ['content'],
    template: '<div class="md-stub">{{ content }}</div>',
  }

  it('渲染助手标题、时间线、正文和复制按钮', async () => {
    const wrapper = mount(AgentReply, {
      props: {
        message: {
          content: '张三本周工时最低',
          createdAt: new Date('2026-10-27T10:43:00').getTime(),
          streaming: false,
          thoughtItems: [{ id: 't1', title: '区间汇总', status: 'success' }],
        },
      },
      global: { stubs: { AgentTimeline: timelineStub, MarkdownMessage: markdownStub } },
    })
    expect(wrapper.text()).toContain('数据智能体')
    expect(wrapper.find('.timeline-stub').text()).toContain('1-false')
    expect(wrapper.find('.md-stub').text()).toContain('张三本周工时最低')
    expect(wrapper.find('.reply-action').text()).toBe('复制')
  })

  it('流式无正文时显示 live line', () => {
    const wrapper = mount(AgentReply, {
      props: {
        message: {
          content: '',
          streaming: true,
          startedAt: Date.now() - 1200,
          thoughtItems: [],
        },
      },
      global: { stubs: { AgentTimeline: timelineStub, MarkdownMessage: markdownStub } },
    })
    expect(wrapper.find('.live-line').exists()).toBe(true)
    expect(wrapper.text()).toContain('正在思考')
  })
})

describe('AgentComposer', () => {
  const stubs = {
    'el-select': { template: '<div class="el-select-stub"><slot /></div>' },
    'el-option': { template: '<div />' },
  }

  it('输入时同步 v-model，发送按钮可用时触发 send', async () => {
    const wrapper = mount(AgentComposer, {
      props: {
        modelValue: '查工时',
        streaming: false,
        providers: [{ id: 1, name: 'p1' }],
        models: ['m1'],
        provider: 'p1',
        model: 'm1',
      },
      global: { stubs },
    })
    await wrapper.find('.composer-input').setValue('查工时')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['查工时'])
    await wrapper.find('.send-button').trigger('click')
    expect(wrapper.emitted('send')).toHaveLength(1)
  })

  it('流式时显示停止按钮并触发 stop', async () => {
    const wrapper = mount(AgentComposer, {
      props: { modelValue: '查工时', streaming: true },
      global: { stubs },
    })
    expect(wrapper.find('.send-button').exists()).toBe(false)
    await wrapper.find('.stop-button').trigger('click')
    expect(wrapper.emitted('stop')).toHaveLength(1)
  })
})
