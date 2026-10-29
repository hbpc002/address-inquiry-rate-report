import { describe, it, expect } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'
import AgentUserMessage from '@/components/AgentUserMessage.vue'
import AgentReply from '@/components/AgentReply.vue'
import AgentComposer from '@/components/AgentComposer.vue'
import AgentAvatar from '@/components/AgentAvatar.vue'
import AgentConversations from '@/components/AgentConversations.vue'
import AgentChat from '@/views/AgentChat.vue'
import { useLauncherStore } from '@/stores/launcher'
import { api } from '@/stores/user'

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

  it('使用悬浮按钮配置的图标与按钮文字，并接入会话列表', () => {
    expect(agentChatVue).toContain('AgentAvatar')
    expect(agentChatVue).toContain('AgentConversations')
    expect(agentChatVue).toContain('launcher.config.label')
    expect(agentChatVue).toContain('launcher.config.icon_value')
    expect(agentChatVue).toContain('store.loadConversations')
    expect(agentChatVue).toContain('store.loadConversation')
    expect(agentChatVue).toContain(':show-owner="isAdmin"')
  })

  it('提供显示思考开关并传给回复组件', () => {
    expect(agentChatVue).toContain('thinking-toggle')
    expect(agentChatVue).toContain('store.showThinking')
    expect(agentChatVue).toContain(':show-thinking="store.showThinking"')
  })

  it('模型选择旁提供快捷问题下拉', () => {
    const composerVue = readFileSync(path.join(root, '../src/components/AgentComposer.vue'), 'utf8')
    expect(composerVue).toContain('快捷问题')
    expect(composerVue).toContain('suggestions')
    expect(composerVue).toContain('onSuggestion')
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

  it('流式时显示当前思考正文，并可折叠', async () => {
    const wrapper = mount(AgentReply, {
      props: {
        message: {
          content: '',
          streaming: true,
          startedAt: Date.now() - 1200,
          thoughtItems: [
            {
              id: 's1',
              kind: 'thinking',
              title: '正在分析问题',
              status: 'loading',
              thinkContent: '先核对考勤，再汇总工时。',
            },
          ],
        },
        showThinking: true,
      },
      global: { stubs: { AgentTimeline: timelineStub, MarkdownMessage: markdownStub } },
    })
    expect(wrapper.find('.live-thought').text()).toContain('当前思考')
    expect(wrapper.find('.live-thought').text()).toContain('先核对考勤')
    await wrapper.find('.live-fold').trigger('click')
    expect(wrapper.find('.live-thought').exists()).toBe(false)
  })

  it('关闭显示思考时不渲染当前思考正文', () => {
    const wrapper = mount(AgentReply, {
      props: {
        message: {
          content: '',
          streaming: true,
          startedAt: Date.now() - 1200,
          thoughtItems: [
            {
              id: 's1',
              kind: 'thinking',
              title: '正在分析问题',
              status: 'loading',
              thinkContent: '先核对考勤。',
            },
          ],
        },
        showThinking: false,
      },
      global: { stubs: { AgentTimeline: timelineStub, MarkdownMessage: markdownStub } },
    })
    expect(wrapper.find('.live-thought').exists()).toBe(false)
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

  it('选择快捷问题后填入输入框', async () => {
    const SelectStub = {
      props: ['modelValue'],
      emits: ['update:modelValue'],
      template: '<button class="suggestion-select-stub" @click="$emit(\'update:modelValue\', \'最近一周谁工时最低\')"><slot /></button>',
    }
    const wrapper = mount(AgentComposer, {
      props: {
        modelValue: '',
        suggestions: ['最近一周谁工时最低'],
      },
      global: {
        stubs: {
          'el-select': SelectStub,
          'el-option': { template: '<div />' },
        },
      },
    })
    await wrapper.find('.suggestion-select-stub').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['最近一周谁工时最低'])
  })
})


describe('AgentAvatar', () => {
  it('渲染 emoji 图标', () => {
    const wrapper = mount(AgentAvatar, {
      props: { type: 'emoji', value: '🤖', size: 36 },
    })
    expect(wrapper.text()).toContain('🤖')
  })

  it('渲染图片与 SVG 图标', () => {
    const image = mount(AgentAvatar, {
      props: { type: 'url', value: '/static/icon.png' },
    })
    expect(image.find('img').attributes('src')).toBe('/static/icon.png')

    const svg = mount(AgentAvatar, {
      props: { type: 'svg', value: '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" /></svg>' },
    })
    expect(svg.find('svg').exists()).toBe(true)
  })
})

describe('AgentConversations', () => {
  const conversations = [
    {
      id: 7,
      title: '最近一周工时',
      is_pinned: true,
      last_message_preview: '谁工时最低',
      last_message_at: new Date().toISOString(),
      owner_name: '张三',
    },
  ]

  it('渲染会话、置顶、管理员归属并支持搜索/新建', async () => {
    const wrapper = mount(AgentConversations, {
      props: {
        conversations,
        activeId: 7,
        total: 1,
        showOwner: true,
        search: '',
      },
    })
    expect(wrapper.text()).toContain('最近一周工时')
    expect(wrapper.text()).toContain('谁工时最低')
    expect(wrapper.text()).toContain('置顶')
    expect(wrapper.text()).toContain('张三')

    await wrapper.find('.new-chat-button').trigger('click')
    await wrapper.find('.search-box input').setValue('工时')
    expect(wrapper.emitted('new')).toHaveLength(1)
    expect(wrapper.emitted('search')?.at(-1)).toEqual(['工时'])
  })

  it('支持选择、置顶、重命名、删除', async () => {
    const wrapper = mount(AgentConversations, {
      props: { conversations, activeId: null },
    })
    await wrapper.find('.conversation-item').trigger('click')
    expect(wrapper.emitted('select')?.[0]).toEqual([7])

    const actions = wrapper.findAll('.conversation-actions button')
    await actions[0].trigger('click')
    await actions[1].trigger('click')
    await actions[2].trigger('click')
    expect(wrapper.emitted('pin')?.[0]?.[0].id).toBe(7)
    expect(wrapper.emitted('rename')?.[0]?.[0].id).toBe(7)
    expect(wrapper.emitted('delete')?.[0]?.[0].id).toBe(7)
  })
})


describe('AgentChat 使用悬浮按钮配置', () => {
  it('顶栏图标和标题来自 launcher 配置', async () => {
    const m = new Map()
    globalThis.localStorage = {
      getItem: (k) => (m.has(k) ? m.get(k) : null),
      setItem: (k, v) => m.set(k, String(v)),
      removeItem: (k) => m.delete(k),
      clear: () => m.clear(),
    }
    setActivePinia(createPinia())
    const launcher = useLauncherStore()
    launcher.setConfig({ label: '小助手', icon_type: 'emoji', icon_value: '🚀' })
    launcher.loaded = true
    vi.spyOn(api, 'get').mockImplementation(async (url) => {
      if (url.includes('/agent/conversations')) return { data: { items: [], total: 0 } }
      if (url.includes('/llm-providers')) return { data: [] }
      return { data: { suggestions: [] } }
    })
    const wrapper = mount(AgentChat, {
      global: {
        stubs: {
          AgentConversations: true,
          AgentComposer: true,
          AgentReply: true,
          AgentUserMessage: true,
        },
      },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('小助手')
    expect(wrapper.text()).toContain('🚀')
  })
})
