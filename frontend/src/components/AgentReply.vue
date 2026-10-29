<template>
  <article class="agent-reply" :class="{ 'is-streaming': streaming }">
    <div class="reply-head">
      <AgentAvatar
        :type="agentIcon.type"
        :value="agentIcon.value"
        :color="agentIcon.color"
        :offset-x="agentIcon.offsetX"
        :offset-y="agentIcon.offsetY"
        :scale="agentIcon.scale"
        :size="22"
      />
      <span class="reply-author">{{ agentName }}</span>
      <time v-if="timeText" class="reply-time">{{ timeText }}</time>
    </div>

    <AgentTimeline
      v-if="steps.length || streaming"
      :steps="steps"
      :streaming="streaming"
      :started-at="message.startedAt"
      :finished-at="message.finishedAt"
      :default-open="false"
      :show-thinking="showThinking"
    />

    <MarkdownMessage v-if="content" :content="content" class="reply-markdown" />

    <section
      v-if="liveThoughtVisible && !thinkingFolded"
      class="live-thought"
      aria-label="思考过程"
    >
      <div class="live-thought-label">{{ liveThoughtLabel }}</div>
      <div
        ref="thoughtBox"
        class="live-thought-text"
        role="region"
        tabindex="0"
        aria-label="思考过程"
        @scroll.passive="onThoughtScroll"
      >{{ liveThoughtText }}</div>
    </section>

    <div v-if="streaming" class="live-line">
      <button
        v-if="liveThoughtVisible"
        type="button"
        class="live-fold"
        :class="{ open: !thinkingFolded }"
        :aria-expanded="!thinkingFolded"
        :aria-label="thinkingFolded ? '展开思考过程' : '收起思考过程'"
        :title="thinkingFolded ? '展开思考过程' : '收起思考过程'"
        @click="thinkingFolded = !thinkingFolded"
      >›</button>
      <span class="live-dot" aria-hidden="true"></span>
      <span class="live-state">{{ liveText }}</span>
      <span v-if="elapsedText" class="live-time">{{ elapsedText }}</span>
    </div>

    <div v-if="!streaming && content" class="reply-actions">
      <button type="button" class="reply-action" @click="copy">
        {{ copied ? '已复制' : '复制' }}
      </button>
    </div>
  </article>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import AgentTimeline from './AgentTimeline.vue'
import AgentAvatar from './AgentAvatar.vue'
import MarkdownMessage from './MarkdownMessage.vue'

const props = defineProps({
  message: { type: Object, required: true },
  agentName: { type: String, default: '数据智能体' },
  showThinking: { type: Boolean, default: true },
  agentIcon: {
    type: Object,
    default: () => ({
      type: 'emoji',
      value: '🤖',
      color: '#5b6ee1',
      offsetX: 0,
      offsetY: 0,
      scale: 100,
    }),
  },
})

const copied = ref(false)
const now = ref(Date.now())
const thinkingFolded = ref(false)
const thoughtBox = ref(null)
const thoughtFollow = ref(true)
let timer = null
let copyTimer = null

const content = computed(() => props.message.content || '')
const steps = computed(() => props.message.thoughtItems || [])
const streaming = computed(() => !!props.message.streaming)

const liveThoughtStep = computed(() => {
  for (let i = steps.value.length - 1; i >= 0; i -= 1) {
    if (steps.value[i].kind === 'thinking') return steps.value[i]
  }
  return null
})

const liveThoughtText = computed(() => {
  const step = liveThoughtStep.value
  if (!step) return ''
  const text = String(step.thinkContent || '').trim()
  return text && text !== String(step.title || '').trim() ? text : ''
})

const liveThoughtVisible = computed(
  () => props.showThinking && streaming.value && !!liveThoughtText.value
)

const liveThoughtLabel = computed(() => {
  const step = liveThoughtStep.value
  return step && step.status === 'loading' ? '当前思考' : '最新思考'
})

const timeText = computed(() => {
  const raw = props.message.createdAt || props.message.startedAt
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

const runningStep = computed(() => {
  for (let i = steps.value.length - 1; i >= 0; i -= 1) {
    if (steps.value[i].status === 'loading') return steps.value[i]
  }
  return null
})

const liveText = computed(() => {
  if (runningStep.value) return `正在执行 · ${runningStep.value.title || '查询'}`
  if (content.value) return '正在整理回答…'
  return '正在思考…'
})

const elapsedText = computed(() => {
  if (!streaming.value || !props.message.startedAt) return ''
  return formatDuration(now.value - props.message.startedAt)
})

function formatDuration(ms) {
  if (ms == null || Number.isNaN(ms)) return ''
  if (ms < 1000) return `${Math.max(0, Math.round(ms))}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m${Math.round(seconds % 60)}s`
}

function startClock() {
  stopClock()
  now.value = Date.now()
  timer = setInterval(() => {
    now.value = Date.now()
  }, 500)
}

function stopClock() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

watch(
  streaming,
  (value) => {
    if (value) {
      startClock()
      thinkingFolded.value = false
      thoughtFollow.value = true
    } else {
      stopClock()
    }
  },
  { immediate: true }
)

watch(
  () => [liveThoughtVisible.value, liveThoughtText.value],
  () => {
    if (!liveThoughtVisible.value || thinkingFolded.value) return
    nextTick(scrollThoughtToBottom)
  }
)

function onThoughtScroll() {
  const el = thoughtBox.value
  if (!el) return
  thoughtFollow.value = el.scrollHeight - el.scrollTop - el.clientHeight < 8
}

function scrollThoughtToBottom() {
  const el = thoughtBox.value
  if (!el || !thoughtFollow.value) return
  el.scrollTop = el.scrollHeight
}

async function copy() {
  try {
    await navigator.clipboard?.writeText(content.value)
    copied.value = true
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch (e) {
    /* 忽略剪贴板权限失败 */
  }
}

onUnmounted(() => {
  stopClock()
  clearTimeout(copyTimer)
})
</script>

<style scoped>
.agent-reply {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  color: var(--agent-text, #1f2026);
}
.reply-head {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 22px;
  font-size: 12.5px;
  line-height: 22px;
}
.reply-author {
  font-weight: 650;
  color: var(--agent-text, #1f2026);
}
.reply-time {
  color: var(--agent-faint, #a3a4ad);
  font-variant-numeric: tabular-nums;
}
.reply-markdown {
  font-size: 14.5px;
  line-height: 1.68;
}
.live-thought {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.live-thought-label {
  color: var(--agent-faint, #a3a4ad);
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.live-thought-text {
  max-height: min(50vh, 320px);
  overflow: auto;
  padding: 9px 11px;
  border: 1px solid var(--agent-line, rgba(31, 32, 38, 0.09));
  border-radius: 8px;
  background: var(--agent-raised, #f0efeb);
  color: var(--agent-muted, #6f7280);
  font-size: 12.5px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.live-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 2px 2px 0;
  color: var(--agent-muted, #6f7280);
  font-size: 13px;
  line-height: 1.5;
}
.live-fold {
  flex: none;
  padding: 0 1px;
  border: 0;
  background: transparent;
  color: var(--agent-faint, #a3a4ad);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  transform: rotate(90deg);
  transition: transform 0.18s ease, color 0.14s ease;
}
.live-fold:hover {
  color: var(--agent-text, #1f2026);
}
.live-fold.open {
  transform: rotate(-90deg);
}
.live-dot {
  width: 7px;
  height: 7px;
  margin-inline: 4px;
  border-radius: 50%;
  background: var(--agent-accent, #5b6ee1);
  box-shadow: 0 0 0 4px var(--agent-accent-soft, #eef0ff);
  animation: agent-live-pulse 1.4s ease-out infinite;
  flex: none;
}
.live-state {
  color: var(--agent-accent, #5b6ee1);
  font-weight: 550;
}
.live-time {
  color: var(--agent-faint, #a3a4ad);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
}
.reply-actions {
  display: flex;
  gap: 6px;
  margin-top: -2px;
}
.reply-action {
  padding: 3px 9px;
  border: 1px solid var(--agent-line, rgba(31, 32, 38, 0.09));
  border-radius: 999px;
  background: transparent;
  color: var(--agent-muted, #6f7280);
  font-size: 11.5px;
  cursor: pointer;
  transition: background-color 0.14s ease, color 0.14s ease;
}
.reply-action:hover {
  background: var(--agent-hover, #f1f0ec);
  color: var(--agent-text, #1f2026);
}
@keyframes agent-live-pulse {
  0% { box-shadow: 0 0 0 0 var(--agent-accent-soft, #eef0ff); }
  70% { box-shadow: 0 0 0 7px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}
@media (prefers-reduced-motion: reduce) {
  .live-dot { animation: none; }
}
</style>
