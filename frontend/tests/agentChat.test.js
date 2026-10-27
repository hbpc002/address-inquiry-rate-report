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
  return globalThis.localStorage
}

describe('agentChat store 持久化', () => {
  beforeEach(() => {
    mockLocalStorage()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('水合：只恢复偏好与当前会话，不再读取本机消息', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    localStorage.setItem(
      'agent_chat_anonymous',
      JSON.stringify({
        bubbleItems: [{ id: 'a1', placement: 'start', content: 'hi', loading: true, thoughtItems: [] }],
        thoughtSeq: 3,
        provider: 'p1',
        model: 'm1',
        conversationId: 7,
      })
    )
    const store = useAgentChatStore()
    store.activate()
    expect(store.bubbleItems.length).toBe(0)
    expect(store.thoughtSeq).toBe(0)
    expect(store.provider).toBe('p1')
    expect(store.model).toBe('m1')
    expect(store.conversationId).toBe(7)
  })

  it('发送后保存消息并刷新本地偏好', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    store.provider = 'p1'
    await new Promise((resolve) => setTimeout(resolve, 0))
    const sse =
      'data: ' + JSON.stringify({ type: 'token', content: '你好' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'tool_start', name: 'query', input: { a: 1 } }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'tool_end', name: 'query', output: { b: 2 } }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'done' }) + '\n\n'
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
              return { done: false, value: enc.encode(sse) }
            },
          }
        },
      },
    }))
    await store.send('在吗')
    expect(store.bubbleItems.length).toBe(2)
    expect(store.bubbleItems[0].placement).toBe('end')
    expect(typeof store.bubbleItems[0].createdAt).toBe('number')
    expect(store.bubbleItems[1].content).toBe('你好')
    expect(typeof store.bubbleItems[1].createdAt).toBe('number')
    expect(store.bubbleItems[1].thoughtItems.length).toBe(1)
    expect(store.bubbleItems[1].thoughtItems[0].status).toBe('success')
    const saved = JSON.parse(localStorage.getItem('agent_chat_anonymous'))
    expect(saved).not.toHaveProperty('bubbleItems')
  })

  it('stop() 中止进行中的流式请求', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
    globalThis.fetch = vi.fn(async (url, opts) => ({
      ok: true,
      body: {
        getReader: () => ({
          read: async () => {
            await sleep(30)
            if (opts.signal.aborted) {
              const e = new Error('aborted')
              e.name = 'AbortError'
              throw e
            }
            return { done: false, value: new TextEncoder().encode('data: ' + JSON.stringify({ type: 'token', content: 'x' }) + '\n\n') }
          },
        }),
      },
    }))
    store.send('在吗')
    await sleep(5)
    store.stop()
    await sleep(60)
    expect(store.streaming).toBe(false)
    expect(store.bubbleItems.length).toBe(2)
  })

  it('status 事件生成思维链 loading 节点并在后续节点结束时置为 success', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    const sse =
      'data: ' + JSON.stringify({ type: 'status', title: '正在分析问题' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'status', title: '正在执行工具：query_date_range' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'token', content: '最近一周' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'done' }) + '\n\n'
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
              return { done: false, value: enc.encode(sse) }
            },
          }
        },
      },
    }))
    await store.send('最近一周')
    const ai = store.bubbleItems[1]
    // 两个 status 各生成一个节点
    expect(ai.thoughtItems.length).toBe(2)
    // token 到来后，最后挂起的 loading 节点应被置为 success
    expect(ai.thoughtItems.every((t) => t.status === 'success')).toBe(true)
    expect(ai.content).toContain('最近一周')
  })

  it('status→tool 序列正确转换节点状态', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    const sse =
      'data: ' + JSON.stringify({ type: 'status', title: '正在分析问题' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'tool_start', name: 'query_date_range', input: { start_date: 'a' } }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'tool_end', name: 'query_date_range', output: { c: 3 } }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'done' }) + '\n\n'
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
              return { done: false, value: enc.encode(sse) }
            },
          }
        },
      },
    }))
    await store.send('最近一周')
    const ai = store.bubbleItems[1]
    expect(ai.thoughtItems.length).toBe(2)
    expect(ai.thoughtItems[0].status).toBe('success')
    expect(ai.thoughtItems[1].title).toBe('区间汇总')
    expect(ai.thoughtItems[1].toolName).toBe('query_date_range')
    expect(ai.thoughtItems[1].status).toBe('success')
    expect(ai.thoughtItems[1].thinkContent).toContain('c')
  })

  it('流式期间 AI 气泡保持 loading=false，步骤实时可见', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    let release
    const gate = new Promise((resolve) => { release = resolve })
    const chunks = [
      'data: ' + JSON.stringify({ type: 'status', id: 'm1', kind: 'thinking', title: '正在分析问题' }) + '\n\n',
      'data: ' + JSON.stringify({ type: 'tool_start', id: 't1', name: 'query_date_range', input: { start_date: '2026-07-01' }, title: '区间汇总', subject: '2026-07-01' }) + '\n\n',
    ]
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      body: {
        getReader: () => {
          const enc = new TextEncoder()
          let index = 0
          return {
            read: async () => {
              if (index < chunks.length) {
                const value = enc.encode(chunks[index])
                index += 1
                return { done: false, value }
              }
              await gate
              return { done: true, value: undefined }
            },
          }
        },
      },
    }))

    const pending = store.send('最近一周')
    await new Promise((resolve) => setTimeout(resolve, 20))
    const ai = store.bubbleItems[1]
    expect(ai.loading).toBe(false)
    expect(ai.streaming).toBe(true)
    expect(store.streaming).toBe(true)
    expect(ai.thoughtItems.length).toBe(2)
    expect(ai.thoughtItems[1].title).toBe('区间汇总')

    release()
    await pending
    expect(ai.loading).toBe(false)
    expect(ai.streaming).toBe(false)
    expect(store.streaming).toBe(false)
    expect(ai.thoughtItems.every((step) => step.status !== 'loading')).toBe(true)
  })

  it('tool_end 按 id 关联并记录耗时、状态和摘要', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    const sse =
      'data: ' + JSON.stringify({ type: 'tool_start', id: 't1', name: 'query_date_range', input: { start_date: '2026-07-01' }, title: '区间汇总', subject: '2026-07-01' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'tool_end', id: 't1', name: 'query_date_range', status: 'success', output: '{"rows":[1,2]}', duration_ms: 42, summary: '返回 2 行' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'tool_start', id: 't2', name: 'run_sql', input: { sql_query: 'select 1' }, title: '自定义查询', subject: 'select 1' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'tool_end', id: 't2', name: 'run_sql', status: 'error', error: 'SQL 超时', duration_ms: 7, summary: '执行失败' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'done' }) + '\n\n'
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
              return { done: false, value: enc.encode(sse) }
            },
          }
        },
      },
    }))

    await store.send('查一下')
    const ai = store.bubbleItems[1]
    expect(ai.thoughtItems.length).toBe(2)
    const [ok, bad] = ai.thoughtItems
    expect(ok.id).toBe('t1')
    expect(ok.status).toBe('success')
    expect(ok.durationMs).toBe(42)
    expect(ok.outcome).toBe('返回 2 行')
    expect(ok.output).toContain('rows')
    expect(bad.id).toBe('t2')
    expect(bad.status).toBe('error')
    expect(bad.durationMs).toBe(7)
    expect(bad.outcome).toBe('执行失败')
    expect(bad.error).toBe('SQL 超时')
  })

  it('加载服务端会话：恢复正文、工具时间线和停止状态', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    vi.spyOn(api, 'get').mockResolvedValue({
      data: {
        id: 7,
        title: '历史会话',
        provider: 'p1',
        model: 'm1',
        messages: [
          {
            id: 1,
            role: 'user',
            content: '查一下',
            events: [],
            status: 'complete',
            created_at: new Date().toISOString(),
          },
          {
            id: 2,
            role: 'assistant',
            content: '结果如下',
            events: [
              { type: 'status', id: 's1', title: '正在分析问题', kind: 'thinking' },
              { type: 'tool_start', id: 't1', name: 'query_date_range', input: { start_date: '2026-07-01' }, title: '区间汇总', subject: '2026-07-01' },
              { type: 'tool_end', id: 't1', status: 'success', output: '{"rows":[1]}', duration_ms: 12, summary: '返回 1 行' },
            ],
            status: 'stopped',
            created_at: new Date().toISOString(),
          },
        ],
      },
    })
    await store.loadConversation(7)
    expect(store.conversationId).toBe(7)
    expect(store.conversationTitle).toBe('历史会话')
    expect(store.bubbleItems.length).toBe(2)
    const ai = store.bubbleItems[1]
    expect(ai.content).toBe('结果如下')
    expect(ai.streaming).toBe(false)
    expect(ai.thoughtItems.length).toBe(2)
    expect(ai.thoughtItems[1].title).toBe('区间汇总')
    expect(ai.thoughtItems[1].status).toBe('success')
  })

  it('progress 事件更新当前 loading 节点的文案而不新增节点', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
    store.activate()
    const sse =
      'data: ' + JSON.stringify({ type: 'status', title: '正在分析问题' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'progress', text: '正在生成查询…' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'progress', text: '正在整理结果…' }) + '\n\n' +
      'data: ' + JSON.stringify({ type: 'done' }) + '\n\n'
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
              return { done: false, value: enc.encode(sse) }
            },
          }
        },
      },
    }))
    await store.send('最近一周')
    const ai = store.bubbleItems[1]
    // progress 只更新不新增节点：仍只有 status 产生的 1 个节点
    expect(ai.thoughtItems.length).toBe(1)
    // 文案被最后一次 progress 更新
    expect(ai.thoughtItems[0].title).toBe('正在整理结果…')
    expect(ai.thoughtItems[0].thinkContent).toBe('正在整理结果…')
  })
})
