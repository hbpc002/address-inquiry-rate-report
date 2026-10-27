<template>
  <div class="agent-timeline" :class="{ 'is-running': streaming, 'is-open': open }">
    <button
      type="button"
      class="timeline-head"
      :aria-expanded="open"
      @click="toggle"
    >
      <span v-if="streaming" class="head-live-dot" aria-hidden="true"></span>
      <span class="head-title">{{ summary }}</span>
      <span v-if="failedCount" class="head-failed">{{ failedCount }} 个失败</span>
      <span v-if="timeText" class="head-time" :class="{ live: streaming }">{{ timeText }}</span>
      <span class="head-chevron" :class="{ open }" aria-hidden="true">›</span>
    </button>
    <Transition name="timeline-body">
      <div v-if="open" class="timeline-body">
        <div class="timeline-line" aria-hidden="true"></div>
        <TransitionGroup name="step-in" tag="div" class="timeline-steps">
          <AgentStep v-for="step in steps" :key="step.id" :step="step" />
        </TransitionGroup>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import AgentStep from './AgentStep.vue'

const props = defineProps({
  steps: { type: Array, default: () => [] },
  streaming: { type: Boolean, default: false },
  startedAt: { type: Number, default: null },
  finishedAt: { type: Number, default: null },
  defaultOpen: { type: Boolean, default: false },
})

const open = ref(props.defaultOpen || props.streaming)
const userToggled = ref(false)
const now = ref(Date.now())
let timer = null

watch(
  () => props.defaultOpen,
  (value) => {
    if (!userToggled.value) open.value = value || props.streaming
  }
)

watch(
  () => props.streaming,
  (value) => {
    if (value) {
      open.value = true
      startClock()
    } else {
      stopClock()
      if (!userToggled.value) open.value = props.defaultOpen
    }
  },
  { immediate: true }
)

watch(
  () => props.steps.length,
  (length, previous) => {
    if (length > previous && props.streaming && !userToggled.value) open.value = true
  }
)

function toggle() {
  userToggled.value = true
  open.value = !open.value
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

onUnmounted(stopClock)

const failedCount = computed(
  () => props.steps.filter((step) => step.status === 'error').length
)

const runningStep = computed(() => {
  for (let i = props.steps.length - 1; i >= 0; i -= 1) {
    if (props.steps[i].status === 'loading') return props.steps[i]
  }
  return null
})

const summary = computed(() => {
  if (props.streaming) {
    return runningStep.value ? `正在执行 · ${runningStep.value.title}` : '正在思考…'
  }
  if (!props.steps.length) return '执行过程'
  return `已完成 ${props.steps.length} 个步骤`
})

const timeText = computed(() => {
  if (props.startedAt == null) return ''
  if (props.streaming) return formatDuration(now.value - props.startedAt)
  if (props.finishedAt != null) return formatDuration(props.finishedAt - props.startedAt)
  const total = props.steps.reduce((sum, step) => sum + (step.durationMs || 0), 0)
  return total ? formatDuration(total) : ''
})

function formatDuration(ms) {
  if (ms == null || Number.isNaN(ms)) return ''
  if (ms < 1000) return `${Math.max(0, Math.round(ms))}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m${Math.round(seconds % 60)}s`
}
</script>

<style scoped>
.agent-timeline {
  min-width: 0;
  border: 1px solid var(--agent-line, rgba(31, 32, 38, 0.09));
  border-radius: var(--agent-radius, 10px);
  background: var(--agent-panel, #fffdf9);
  overflow: hidden;
}
.agent-timeline.is-open {
  background: var(--agent-panel, #fffdf9);
}
.timeline-head {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  min-height: 38px;
  padding: 0 12px;
  border: 0;
  background: transparent;
  color: var(--agent-muted, #6f7280);
  font-size: 13px;
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.14s ease, color 0.14s ease;
}
.timeline-head:hover {
  background: var(--agent-hover, #f1f0ec);
  color: var(--agent-text, #1f2026);
}
.timeline-head:focus-visible {
  outline-offset: -2px;
}
.head-live-dot {
  width: 7px;
  height: 7px;
  margin-inline: 2px;
  border-radius: 50%;
  background: var(--agent-accent, #5b6ee1);
  box-shadow: 0 0 0 4px var(--agent-accent-soft, #eef0ff);
  animation: agent-head-pulse 1.4s ease-out infinite;
  flex: none;
}
.head-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 550;
}
.head-failed {
  flex: none;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--agent-err-soft, #fdeef1);
  color: var(--agent-err, #c25566);
  font-size: 10.5px;
  font-weight: 550;
}
.head-time {
  flex: none;
  color: var(--agent-faint, #a3a4ad);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
}
.head-time.live {
  color: var(--agent-accent, #5b6ee1);
}
.head-chevron {
  flex: none;
  color: var(--agent-faint, #a3a4ad);
  font-size: 16px;
  line-height: 1;
  transform: rotate(90deg);
  transition: transform 0.18s ease;
}
.head-chevron.open {
  transform: rotate(-90deg);
}
.timeline-body {
  position: relative;
  padding: 2px 8px 8px;
  border-top: 1px solid var(--agent-line, rgba(31, 32, 38, 0.09));
}
.timeline-line {
  position: absolute;
  left: 17px;
  top: 2px;
  bottom: 12px;
  width: 1px;
  background: var(--agent-line-strong, rgba(31, 32, 38, 0.12));
}
.timeline-steps {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.step-in-enter-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.step-in-enter-from {
  opacity: 0;
  transform: translateY(-5px);
}
.timeline-body-enter-active,
.timeline-body-leave-active {
  transition: opacity 0.15s ease;
}
.timeline-body-enter-from,
.timeline-body-leave-to {
  opacity: 0;
}
@keyframes agent-head-pulse {
  0% { box-shadow: 0 0 0 0 var(--agent-accent-soft, #eef0ff); }
  70% { box-shadow: 0 0 0 7px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}
@media (prefers-reduced-motion: reduce) {
  .head-live-dot { animation: none; }
  .head-chevron,
  .step-in-enter-active,
  .timeline-body-enter-active,
  .timeline-body-leave-active { transition: none; }
}
</style>
