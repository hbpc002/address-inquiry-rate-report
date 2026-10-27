import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'

const TOOL_TITLES = {
  query_team_ranking: '班组排名',
  query_month_summary: '月度汇总',
  query_date_range: '区间汇总',
  query_daily: '每日明细',
  query_efficiency: '月度效能',
  query_dashboard_stats: '仪表盘统计',
  run_sql: '自定义查询',
}

const SUBJECT_KEYS = [
  'year_month',
  'start_date',
  'end_date',
  'schedule_date',
  'emp_name',
  'team',
  'month',
  'name',
]

function short(v) {
  if (v == null) return ''
  let s
  if (typeof v === 'string') {
    s = v
  } else {
    try {
      s = JSON.stringify(v)
    } catch (e) {
      s = String(v)
    }
  }
  if (s == null) s = String(v)
  return s.length > 300 ? s.slice(0, 300) + '…' : s
}

function toolTitle(name) {
  return TOOL_TITLES[name] || name || '工具'
}

function toolSubject(name, input) {
  if (input == null) return ''
  if (typeof input !== 'object') return short(input)
  if (name === 'run_sql') {
    return short(input.sql_query || input.sql || '')
  }
  const parts = []
  for (const key of SUBJECT_KEYS) {
    const value = input[key]
    if (value !== undefined && value !== null && value !== '') parts.push(String(value))
  }
  if (parts.length) return parts.join(' · ')
  return Object.keys(input)
    .slice(0, 2)
    .map((key) => `${key}=${short(input[key])}`)
    .join(' · ')
}

function outputText(output) {
  if (output == null) return ''
  if (typeof output === 'string') return output
  try {
    return JSON.stringify(output)
  } catch (e) {
    return String(output)
  }
}

function outcomeOf(output) {
  const text = outputText(output)
  if (!text) return ''
  try {
    const data = JSON.parse(text)
    if (Array.isArray(data)) return `返回 ${data.length} 行`
    if (data && typeof data === 'object') {
      for (const key of ['rows', 'data', 'items', 'result']) {
        if (Array.isArray(data[key])) return `返回 ${data[key].length} 行`
      }
      if (data.error) return '查询失败'
    }
  } catch (e) {
    /* 非 JSON 输出 */
  }
  const lines = text.split('\n').filter((line) => line.trim()).length
  return lines ? `${lines} 行输出` : ''
}

function formatDuration(ms) {
  if (ms == null || Number.isNaN(ms)) return ''
  if (ms < 1000) return `${Math.max(0, Math.round(ms))}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m${Math.round(seconds % 60)}s`
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
        bubbleItems.value = saved.bubbleItems.map((m) => ({
          ...m,
          loading: false,
          streaming: false,
          thoughtItems: (m.thoughtItems || []).map((t) => ({
            ...t,
            thinkTitle: t.thinkTitle || t.title || '',
            status: t.status === 'loading' ? 'stopped' : t.status,
          })),
        }))
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

  function _newStep({ id, kind, title, thinkContent = '' }) {
    const now = Date.now()
    return {
      id,
      kind: kind || 'status',
      title: title || '正在处理',
      thinkTitle: title || '正在处理',
      thinkContent,
      status: 'loading',
      isCanExpand: true,
      startedAt: now,
      endedAt: null,
      durationMs: null,
      input: null,
      output: null,
      subject: '',
      outcome: '',
      error: '',
    }
  }

  function _finishStep(step, status) {
    if (!step || step.status !== 'loading') return
    step.status = status || 'success'
    step.endedAt = Date.now()
    step.durationMs = step.startedAt ? step.endedAt - step.startedAt : null
  }

  function _finalizeNonToolLoading(status = 'success') {
    for (const step of _thinkingList()) {
      if (step.status === 'loading' && step.kind !== 'tool') _finishStep(step, status)
    }
  }

  function _finalizeAll(status = 'success') {
    for (const step of _thinkingList()) {
      if (step.status === 'loading') _finishStep(step, status)
    }
    pendingThoughtId.value = null
  }

  function _findStep(id) {
    if (id == null) return null
    return _thinkingList().find((step) => step.id === id) || null
  }

  function _lastLoading(kind) {
    const list = _thinkingList()
    for (let i = list.length - 1; i >= 0; i -= 1) {
      if (list[i].status === 'loading' && (!kind || list[i].kind === kind)) return list[i]
    }
    return null
  }

  function _addStatus(title, id, kind = 'status') {
    const it = _ai()
    if (!it) return
    _finalizeNonToolLoading()
    const sid = id || 's' + ++thoughtSeq.value
    const existing = id != null ? _findStep(sid) : null
    if (existing) {
      existing.title = title || existing.title
      existing.thinkTitle = existing.title
      existing.thinkContent = title || existing.thinkContent
      existing.status = 'loading'
      existing.kind = kind || existing.kind
      existing.startedAt = existing.startedAt || Date.now()
      pendingThoughtId.value = sid
      return
    }
    pendingThoughtId.value = sid
    it.thoughtItems = it.thoughtItems || []
    it.thoughtItems.push(_newStep({ id: sid, kind, title, thinkContent: title || '正在处理…' }))
  }

  function _addTool(name, input, id, title, subject) {
    const it = _ai()
    if (!it) return
    _finalizeNonToolLoading()
    const tid = id || 't' + ++thoughtSeq.value
    pendingThoughtId.value = tid
    const step = _newStep({
      id: tid,
      kind: 'tool',
      title: title || toolTitle(name),
      thinkContent: '入参：' + short(input),
    })
    step.toolName = name || ''
    step.input = input
    step.subject = subject || toolSubject(name, input)
    it.thoughtItems = it.thoughtItems || []
    it.thoughtItems.push(step)
  }

  function clear() {
    if (abortCtl.value) abortCtl.value.abort()
    bubbleItems.value = []
    currentAiId.value = null
    thoughtSeq.value = 0
    pendingThoughtId.value = null
    streaming.value = false
  }

  function stop() {
    if (abortCtl.value) abortCtl.value.abort()
  }

  function handleEvent(evt) {
    const it = _ai()
    if (!it) return
    if (evt.type === 'token') {
      _finalizeNonToolLoading()
      it.content += evt.content
    } else if (evt.type === 'status') {
      _addStatus(evt.title, evt.id, evt.kind || 'thinking')
    } else if (evt.type === 'progress') {
      const pending = _findStep(evt.id) || _lastLoading('thinking') || _lastLoading()
      if (pending && evt.text) {
        pending.title = evt.text
        pending.thinkTitle = evt.text
        pending.thinkContent = evt.text
      }
    } else if (evt.type === 'tool_start') {
      _addTool(evt.name, evt.input, evt.id, evt.title, evt.subject)
    } else if (evt.type === 'tool_end') {
      const item = _findStep(evt.id) || _lastLoading('tool')
      if (item) {
        item.status = evt.status === 'error' ? 'error' : 'success'
        item.endedAt = Date.now()
        item.durationMs = evt.duration_ms != null
          ? evt.duration_ms
          : item.startedAt ? item.endedAt - item.startedAt : null
        item.output = evt.output || ''
        item.error = evt.error || ''
        item.outcome = evt.summary || (item.status === 'error' ? '执行失败' : outcomeOf(evt.output))
        const tail = evt.status === 'error'
          ? '\n结果：' + short(evt.error || '执行失败')
          : '\n结果：' + short(evt.output)
        item.thinkContent += tail
      }
      pendingThoughtId.value = null
    } else if (evt.type === 'done') {
      _finalizeAll('success')
      it.finishedAt = Date.now()
    } else if (evt.type === 'notice') {
      _finalizeNonToolLoading()
      it.content += `\n\n> ℹ️ ${evt.message || ''}`
    } else if (evt.type === 'error') {
      const pending = _lastLoading()
      if (pending) {
        pending.error = evt.message || '执行失败'
        pending.outcome = '执行失败'
        _finishStep(pending, 'error')
      } else {
        _finalizeNonToolLoading('error')
      }
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
    bubbleItems.value.push({
      id: aid,
      placement: 'start',
      content: '',
      variant: 'filled',
      loading: false,
      streaming: true,
      startedAt: Date.now(),
      finishedAt: null,
      thoughtItems: [],
    })
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
      const wasAborted = !!(abortCtl.value && abortCtl.value.signal.aborted)
      streaming.value = false
      const it = _ai()
      if (it) {
        it.loading = false
        it.streaming = false
        it.finishedAt = it.finishedAt || Date.now()
      }
      _finalizeAll(wasAborted ? 'stopped' : 'success')
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
    formatDuration,
  }
})
