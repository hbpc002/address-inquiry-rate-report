import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'

function short(v) {
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 300 ? s.slice(0, 300) + '…' : s
}

function lsKey() {
  const user = useUserStore().user
  const uid = user?.id != null ? String(user.id) : 'anonymous'
  return `agent_chat_${uid}`
}

export const useAgentChatStore = defineStore('agentChat', () => {
  const bubbleItems = ref([])
  const input = ref('')
  const streaming = ref(false)
  const currentAiId = ref(null)
  const thoughtSeq = ref(0)
  const pendingThoughtId = ref(null)
  const abortCtl = ref(null)
  const provider = ref('')
  const model = ref('')

  let _boundKey = null

  function _hydrate(key) {
    _boundKey = key
    try {
      const saved = JSON.parse(localStorage.getItem(key) || 'null')
      if (saved && Array.isArray(saved.bubbleItems)) {
        bubbleItems.value = saved.bubbleItems.map((m) => ({ ...m, loading: false }))
        thoughtSeq.value = saved.thoughtSeq || 0
        provider.value = saved.provider || ''
        model.value = saved.model || ''
        return
      }
    } catch (e) { /* 忽略损坏数据 */ }
    bubbleItems.value = []
    thoughtSeq.value = 0
    provider.value = ''
    model.value = ''
  }

  function activate() {
    const key = lsKey()
    if (key === _boundKey) return
    _hydrate(key)
  }

  watch(
    [bubbleItems, provider, model],
    () => {
      if (!_boundKey) return
      try {
        localStorage.setItem(
          _boundKey,
          JSON.stringify({
            bubbleItems: bubbleItems.value,
            thoughtSeq: thoughtSeq.value,
            provider: provider.value,
            model: model.value,
          })
        )
      } catch (e) {
        /* 容量超限忽略 */
      }
    },
    { deep: true }
  )

  function _ai() {
    return bubbleItems.value.find((m) => m.id === currentAiId.value) || null
  }

  function _thinkingList() {
    const it = _ai()
    if (!it) return []
    if (!it.thoughtItems) it.thoughtItems = []
    return it.thoughtItems
  }

  // 结束当前挂起中的 loading 节点
  function _finalizePending(onlyId = null) {
    const list = _thinkingList()
    const it = _ai()
    if (!it) return
    for (const t of list) {
      if (t.status === 'loading' && (onlyId == null || t.id === onlyId)) {
        t.status = 'success'
        if (onlyId != null) break
      }
    }
    if (onlyId != null) pendingThoughtId.value = null
  }

  function _addStatus(title) {
    const it = _ai()
    if (!it) return
    _finalizePending()
    const id = 's' + ++thoughtSeq.value
    pendingThoughtId.value = id
    it.thoughtItems = it.thoughtItems || []
    it.thoughtItems.push({
      id,
      title: title || '正在处理',
      thinkContent: '正在处理…',
      status: 'loading',
      isCanExpand: true,
    })
  }

  function _addTool(name, input) {
    const it = _ai()
    if (!it) return
    _finalizePending()
    const id = 't' + ++thoughtSeq.value
    pendingThoughtId.value = id
    if (!it.thoughtItems) it.thoughtItems = []
    it.thoughtItems.push({
      id,
      title: name || '工具',
      thinkContent: '入参：' + short(input),
      status: 'loading',
      isCanExpand: true,
    })
  }

  function clear() {
    bubbleItems.value = []
    currentAiId.value = null
    thoughtSeq.value = 0
    pendingThoughtId.value = null
  }

  function stop() {
    if (abortCtl.value) abortCtl.value.abort()
  }

  function handleEvent(evt) {
    const it = _ai()
    if (!it) return
    if (evt.type === 'token') {
      _finalizePending()
      it.content += evt.content
    } else if (evt.type === 'status') {
      _addStatus(evt.title)
    } else if (evt.type === 'tool_start') {
      _addTool(evt.name, evt.input)
    } else if (evt.type === 'tool_end') {
      const item = _thinkingList().find((t) => t.id === pendingThoughtId.value)
      if (item) {
        item.status = 'success'
        item.thinkContent += '\n结果：' + short(evt.output)
      }
      pendingThoughtId.value = null
    } else if (evt.type === 'notice') {
      _finalizePending()
      it.content += `\n\n> ℹ️ ${evt.message || ''}`
    } else if (evt.type === 'error') {
      _finalizePending()
      it.content += `\n\n> ⚠️ ${evt.message || '未知错误'}`
    }
  }

  async function send(text) {
    const q = (text != null ? text : input.value).trim()
    if (!q || streaming.value) return
    input.value = ''
    const uid = 'u' + Date.now() + Math.random().toString(36).slice(2, 6)
    bubbleItems.value.push({ id: uid, placement: 'end', content: q, variant: 'filled' })
    const aid = 'a' + Date.now() + Math.random().toString(36).slice(2, 6)
    bubbleItems.value.push({ id: aid, placement: 'start', content: '', variant: 'filled', loading: true, thoughtItems: [] })
    currentAiId.value = aid
    streaming.value = true
    abortCtl.value = new AbortController()
    const token = localStorage.getItem('token')
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = 'Bearer ' + token
    try {
      const resp = await fetch('/api/agent/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: q,
          provider: provider.value || undefined,
          model: model.value || undefined,
        }),
        signal: abortCtl.value.signal,
      })
      if (!resp.ok || !resp.body) {
        const it = _ai()
        if (it) it.content += '\n\n> ⚠️ 请求失败（HTTP ' + (resp && resp.status) + '）'
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buffer.indexOf('\n\n')) >= 0) {
          const chunk = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          const line = chunk.replace(/^data: /, '')
          if (!line.trim()) continue
          let evt
          try {
            evt = JSON.parse(line)
          } catch (e) {
            continue
          }
          handleEvent(evt)
        }
      }
    } catch (e) {
      if (e && e.name !== 'AbortError') {
        const it = _ai()
        if (it) it.content += `\n\n> ⚠️ ${e.message || '请求失败'}`
      }
    } finally {
      streaming.value = false
      const it = _ai()
      if (it) it.loading = false
      currentAiId.value = null
      abortCtl.value = null
    }
  }

  return {
    bubbleItems,
    input,
    streaming,
    currentAiId,
    thoughtSeq,
    pendingThoughtId,
    abortCtl,
    provider,
    model,
    activate,
    clear,
    stop,
    send,
  }
})
