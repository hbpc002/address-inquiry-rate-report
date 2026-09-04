import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

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

  it('水合：从 localStorage 恢复对话并清除残留 loading', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    localStorage.setItem(
      'agent_chat',
      JSON.stringify({
        bubbleItems: [{ id: 'a1', placement: 'start', content: 'hi', loading: true, thoughtItems: [] }],
        thoughtSeq: 3,
        provider: 'p1',
        model: 'm1',
      })
    )
    const store = useAgentChatStore()
    expect(store.bubbleItems.length).toBe(1)
    expect(store.bubbleItems[0].loading).toBe(false)
    expect(store.bubbleItems[0].content).toBe('hi')
    expect(store.thoughtSeq).toBe(3)
    expect(store.provider).toBe('p1')
    expect(store.model).toBe('m1')
  })

  it('发送后把对话写回 localStorage', async () => {
    const { useAgentChatStore } = await import('@/stores/agentChat')
    const store = useAgentChatStore()
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
    expect(store.bubbleItems[1].content).toBe('你好')
    expect(store.bubbleItems[1].thoughtItems.length).toBe(1)
    expect(store.bubbleItems[1].thoughtItems[0].status).toBe('success')
    const saved = JSON.parse(localStorage.getItem('agent_chat'))
    expect(saved.bubbleItems.length).toBe(2)
    expect(saved.bubbleItems[1].content).toBe('你好')
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
    expect(ai.thoughtItems[1].title).toBe('query_date_range')
    expect(ai.thoughtItems[1].status).toBe('success')
    expect(ai.thoughtItems[1].thinkContent).toContain('c')
  })
})
