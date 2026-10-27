import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { api } from '@/stores/user'

function mockLocalStorage() {
  const m = new Map()
  globalThis.localStorage = {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    clear: () => m.clear(),
  }
}

function sse(events) {
  return events.map((e) => 'data: ' + JSON.stringify(e) + '\n\n').join('')
}

function mockStream(payload) {
  globalThis.fetch = vi.fn(async () => ({
    ok: true,
    body: {
      getReader: () => {
        const enc = new TextEncoder()
        let sent = false
        return {
          read: async () => {
            if (sent) return { done: true, value: undefined }
            sent = true
            return { done: false, value: enc.encode(payload) }
          },
        }
      },
    },
  }))
}

describe('agentChat 会话管理', () => {
  beforeEach(() => {
    mockLocalStorage()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('加载会话列表并恢复指定会话', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    vi.spyOn(api, 'get')
      .mockResolvedValueOnce({
        data: {
          items: [
            { id: 7, title: '历史会话', is_pinned: true, message_count: 2 },
          ],
          total: 1,
        },
      })
      .mockResolvedValueOnce({
        data: {
          id: 7,
          title: '历史会话',
          provider: 'p1',
          model: 'm1',
          messages: [
            { id: 1, role: 'user', content: '问题', status: 'complete', events: [], created_at: new Date().toISOString() },
            { id: 2, role: 'assistant', content: '回答', status: 'complete', events: [], created_at: new Date().toISOString() },
          ],
        },
      })

    await store.loadConversations()
    expect(store.conversations).toHaveLength(1)
    expect(store.conversationsTotal).toBe(1)

    await store.loadConversation(7)
    expect(store.conversationId).toBe(7)
    expect(store.conversationTitle).toBe('历史会话')
    expect(store.bubbleItems).toHaveLength(2)
    expect(store.bubbleItems[1].content).toBe('回答')
  })

  it('重命名、置顶、删除会话', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    store.conversations = [
      { id: 7, title: '旧标题', is_pinned: false, message_count: 2 },
    ]
    store.conversationId = 7
    store.conversationTitle = '旧标题'

    vi.spyOn(api, 'patch')
      .mockResolvedValueOnce({ data: { id: 7, title: '新标题', is_pinned: false } })
      .mockResolvedValueOnce({ data: { id: 7, title: '新标题', is_pinned: true } })
    vi.spyOn(api, 'get').mockResolvedValue({
      data: { items: [{ id: 7, title: '新标题', is_pinned: true }], total: 1 },
    })
    vi.spyOn(api, 'delete').mockResolvedValue({ data: { message: 'ok' } })

    await store.renameConversation(7, '新标题')
    expect(store.conversationTitle).toBe('新标题')

    await store.togglePin(7)
    expect(store.conversations[0].is_pinned).toBe(true)

    await store.deleteConversation(7)
    expect(store.conversations).toHaveLength(0)
    expect(store.conversationId).toBeNull()
  })

  it('发送时携带 conversation_id，并处理 meta 事件', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    store.conversationId = 5
    store.provider = 'p1'
    store.model = 'm1'
    vi.spyOn(api, 'get').mockResolvedValue({ data: { items: [], total: 0 } })
    mockStream(sse([
      { type: 'meta', conversation_id: 9, title: '新标题', assistant_message_id: 88 },
      { type: 'token', content: '你好' },
      { type: 'done' },
    ]))

    await store.send('继续问')

    const body = JSON.parse(globalThis.fetch.mock.calls[0][1].body)
    expect(body.conversation_id).toBe(5)
    expect(store.conversationId).toBe(9)
    expect(store.conversationTitle).toBe('新标题')
    expect(store.bubbleItems[1].serverId).toBe(88)
    expect(store.bubbleItems[1].content).toBe('你好')
  })

  it('新对话清空当前消息但不删除会话列表', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    store.conversations = [{ id: 7, title: '保留' }]
    store.bubbleItems = [{ id: 'u1', placement: 'end', content: '旧消息' }]
    store.conversationId = 7
    store.conversationTitle = '旧会话'

    store.newConversation()

    expect(store.bubbleItems).toHaveLength(0)
    expect(store.conversationId).toBeNull()
    expect(store.conversationTitle).toBe('')
    expect(store.conversations).toHaveLength(1)
  })
})
