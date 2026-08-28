<template>
  <div class="agent-chat">
    <div class="agent-header">
      <div class="title">智能体 · 自然语言查报表</div>
      <div class="header-right">
        <el-button size="small" text @click="clearMessages">清空</el-button>
      </div>
    </div>

    <div class="messages" ref="messagesRef">
      <div v-if="!bubbleItems.length" class="empty">
        <Prompts :items="promptItems" :wrap="true" @itemClick="onPrompt" />
      </div>

      <BubbleList v-else :list="bubbleItems" :auto-scroll="true" class="bubble-list">
        <template #content="{ item }">
          <div class="bubble-body">
            <ThoughtChain
              v-if="item.thoughtItems && item.thoughtItems.length"
              :thinking-items="item.thoughtItems"
              class="thought-chain"
            />
            <MarkdownMessage v-if="item.placement === 'start'" :content="item.content" />
            <span v-else class="user-text">{{ item.content }}</span>
          </div>
        </template>
      </BubbleList>
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
import { ref, nextTick } from 'vue'
import { BubbleList, ThoughtChain, Prompts } from 'vue-element-plus-x'
import { api } from '@/stores/user'
import MarkdownMessage from '@/components/MarkdownMessage.vue'

const props = defineProps({
  embedded: { type: Boolean, default: false },
})

const bubbleItems = ref([])
const input = ref('')
const streaming = ref(false)
const messagesRef = ref(null)
const abortCtl = ref(null)
let currentAi = null
let thoughtSeq = 0
let pendingThoughtId = null

const suggestions = [
  '2026-07 各班组出勤率排名',
  '最近一周谁工时最低',
  '导出 7 月考勤报表',
  '本月迟到次数最多的人',
]
const promptItems = suggestions.map((label, i) => ({ key: String(i), label }))

function short(v) {
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 300 ? s.slice(0, 300) + '…' : s
}

function scrollBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

function clearMessages() {
  bubbleItems.value = []
  currentAi = null
}

function onPrompt(item) {
  if (item && item.label) send(item.label)
}

async function send(text) {
  const q = (text != null ? text : input.value).trim()
  if (!q || streaming.value) return
  input.value = ''
  bubbleItems.value.push({ id: `u${Date.now()}`, placement: 'end', content: q, variant: 'filled' })
  currentAi = { id: `a${Date.now()}`, placement: 'start', content: '', variant: 'filled', loading: true, thoughtItems: [] }
  bubbleItems.value.push(currentAi)
  streaming.value = true
  scrollBottom()

  abortCtl.value = new AbortController()
  const token = localStorage.getItem('token')
  try {
    const resp = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ message: q }),
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
        handleEvent(evt)
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError' && currentAi) currentAi.content += `\n\n> ⚠️ ${e.message || '请求失败'}`
  } finally {
    streaming.value = false
    if (currentAi) currentAi.loading = false
    currentAi = null
    abortCtl.value = null
    scrollBottom()
  }
}

function handleEvent(evt) {
  if (!currentAi) return
  if (evt.type === 'token') {
    currentAi.content += evt.content
  } else if (evt.type === 'tool_start') {
    const id = `t${++thoughtSeq}`
    pendingThoughtId = id
    currentAi.thoughtItems.push({
      id,
      title: evt.name,
      thinkContent: '入参：' + short(evt.input),
      status: 'loading',
      isCanExpand: true,
    })
  } else if (evt.type === 'tool_end') {
    const item = currentAi.thoughtItems.find(t => t.id === pendingThoughtId)
    if (item) {
      item.status = 'success'
      item.thinkContent += '\n结果：' + short(evt.output)
    }
    pendingThoughtId = null
  } else if (evt.type === 'error') {
    currentAi.content += `\n\n> ⚠️ ${evt.message}`
  }
  scrollBottom()
}

function stop() {
  abortCtl.value?.abort()
}
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
.bubble-list { background: transparent; }
.bubble-body { word-break: break-word; }
.user-text { white-space: pre-wrap; }
.thought-chain { margin-bottom: 8px; }
.input-bar {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid #ebeef5;
  align-items: flex-end;
}
.input-bar .el-input { flex: 1; }
</style>
