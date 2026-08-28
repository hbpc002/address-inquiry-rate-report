<template>
  <div class="agent-chat">
    <div class="agent-header">
      <div class="title">智能体 · 自然语言查报表</div>
      <div class="header-right">
        <el-select v-if="providers.length" v-model="selectedProvider" size="small" placeholder="默认模型" style="width:160px">
          <el-option label="默认模型" value="" />
          <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.name" />
        </el-select>
        <el-button size="small" text @click="clearMessages">清空</el-button>
      </div>
    </div>

    <div class="messages" ref="messagesRef">
      <div v-if="!messages.length" class="empty">
        <p>试试这样问我：</p>
        <div class="chips">
          <el-button v-for="q in suggestions" :key="q" size="small" round @click="send(q)">{{ q }}</el-button>
        </div>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
        <div class="bubble">
          <template v-if="m.role === 'user'">
            <div class="user-text">{{ m.content }}</div>
          </template>
          <template v-else>
            <el-collapse v-if="m.steps && m.steps.length" class="thought" :model-value="['thought']">
              <el-collapse-item name="thought" title="推理过程">
                <el-timeline>
                  <el-timeline-item
                    v-for="(s, si) in m.steps"
                    :key="si"
                    :type="s.status === 'done' ? 'success' : 'primary'"
                    :hollow="s.status !== 'done'"
                  >
                    <div class="step-name">🔧 {{ s.name }}</div>
                    <div v-if="s.input" class="step-io">入参：{{ short(s.input) }}</div>
                    <div v-if="s.output" class="step-io">结果：{{ short(s.output) }}</div>
                  </el-timeline-item>
                </el-timeline>
              </el-collapse-item>
            </el-collapse>
            <MarkdownMessage :content="m.content" />
          </template>
        </div>
      </div>
      <div v-if="streaming" class="msg-row assistant"><div class="bubble typing"><span class="dot">●</span> 思考中…</div></div>
    </div>

    <div class="input-bar">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        resize="none"
        placeholder="输入问题，Enter 发送 / Shift+Enter 换行"
        @keydown.enter.exact.prevent="send()"
      />
      <el-button v-if="!streaming" type="primary" :disabled="!input.trim()" @click="send()">发送</el-button>
      <el-button v-else type="danger" @click="stop()">停止</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { api } from '@/stores/user'
import MarkdownMessage from '@/components/MarkdownMessage.vue'

const props = defineProps({
  embedded: { type: Boolean, default: false },
})

const messages = ref([])
const input = ref('')
const streaming = ref(false)
const providers = ref([])
const selectedProvider = ref('')
const messagesRef = ref(null)
const abortCtl = ref(null)

const suggestions = [
  '2026-07 各班组出勤率排名',
  '最近一周谁工时最低',
  '导出 7 月考勤报表',
  '本月迟到次数最多的人',
]

function short(v) {
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 200 ? s.slice(0, 200) + '…' : s
}

async function loadProviders() {
  try {
    const r = await api.get('/llm-providers')
    providers.value = r.data || []
  } catch (e) {
    providers.value = []
  }
}

function scrollBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

function clearMessages() {
  messages.value = []
}

function handleEvent(evt, assistant) {
  if (evt.type === 'token') {
    assistant.content += evt.content
  } else if (evt.type === 'tool_start') {
    assistant.steps.push({ name: evt.name, input: evt.input, status: 'running', output: '' })
  } else if (evt.type === 'tool_end') {
    const step = [...assistant.steps].reverse().find(s => s.status === 'running' && s.name === evt.name)
    if (step) { step.status = 'done'; step.output = evt.output }
    else assistant.steps.push({ name: evt.name, input: '', status: 'done', output: evt.output })
  } else if (evt.type === 'done') {
    assistant.done = true
  } else if (evt.type === 'error') {
    assistant.content += `\n\n> ⚠️ ${evt.message}`
    assistant.done = true
  }
  scrollBottom()
}

async function send(text) {
  const q = (text != null ? text : input.value).trim()
  if (!q || streaming.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: q })
  const assistant = { role: 'assistant', content: '', steps: [], done: false }
  messages.value.push(assistant)
  streaming.value = true
  scrollBottom()

  abortCtl.value = new AbortController()
  const token = localStorage.getItem('token')
  try {
    const resp = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ message: q, provider: selectedProvider.value || undefined }),
      signal: abortCtl.value.signal,
    })
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let idx
      while ((idx = buffer.indexOf('\n\n')) >= 0) {
        const chunk = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)
        const line = chunk.replace(/^data: /, '')
        if (!line.trim()) continue
        let evt
        try { evt = JSON.parse(line) } catch { continue }
        handleEvent(evt, assistant)
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') assistant.content += `\n\n> ⚠️ ${e.message || '请求失败'}`
  } finally {
    streaming.value = false
    assistant.done = true
    abortCtl.value = null
  }
}

function stop() {
  abortCtl.value?.abort()
}

onMounted(loadProviders)
</script>

<style scoped>
.agent-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 420px;
}
.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #ebeef5;
}
.title { font-weight: 600; }
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f7f8fa;
}
.empty { text-align: center; color: #909399; margin-top: 40px; }
.chips { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
.msg-row { display: flex; margin-bottom: 14px; }
.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }
.bubble {
  max-width: 82%;
  padding: 10px 14px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.msg-row.user .bubble { background: #ecf5ff; }
.thought { margin-bottom: 8px; }
.step-name { font-weight: 600; }
.step-io { font-size: 12px; color: #909399; word-break: break-all; }
.typing .dot { animation: blink 1s infinite; color: #409eff; }
@keyframes blink { 50% { opacity: 0.2; } }
.input-bar {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid #ebeef5;
  align-items: flex-end;
}
.input-bar .el-input { flex: 1; }
</style>
