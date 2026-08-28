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
})
