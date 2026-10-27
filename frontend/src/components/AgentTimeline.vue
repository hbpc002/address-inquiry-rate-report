<template>
  <div class="agent-timeline" :class="{ 'is-running': streaming }">
    <button type="button" class="timeline-head" @click="open = !open">
      <span class="head-chevron" :class="{ open }">›</span>
      <span class="head-title">{{ summary }}</span>
      <span v-if="failedCount" class="head-failed">{{ failedCount }} 个失败</span>
      <span v-if="timeText" class="head-time" :class="{ live: streaming }">{{ timeText }}</span>
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
const now = ref(Date.now())
let timer = null

watch(
  () => props.defaultOpen,
  (value) => {
    if (value) open.value = true
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
    }
  },
  { immediate: true }
)

watch(
  () => props.steps.length,
  (length, previous) => {
    if (length > previous && props.streaming) open.value = true
  }
)

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
  margin-bottom: 8px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafbfc;
  overflow: hidden;
}
.timeline-head {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 7px 10px;
  border: 0;
  background: transparent;
  color: #606266;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}
.timeline-head:hover {
  background: #f2f5f9;
}
.head-chevron {
  color: #a8abb2;
  font-size: 15px;
  line-height: 1;
  transition: transform 0.18s ease;
  transform: rotate(90deg);
  flex-shrink: 0;
}
.head-chevron.open {
  transform: rotate(-90deg);
}
.head-title {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.head-failed {
  padding: 0 6px;
  border-radius: 8px;
  background: #fef0f0;
  color: #f56c6c;
  font-size: 10px;
  line-height: 16px;
  flex-shrink: 0;
}
.head-time {
  margin-left: auto;
  color: #909399;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.head-time.live {
  color: #409eff;
}
.timeline-body {
  position: relative;
  padding: 2px 8px 8px;
}
.timeline-line {
  position: absolute;
  left: 16px;
  top: 4px;
  bottom: 12px;
  width: 1px;
  background: #e4e7ed;
}
.timeline-steps {
  display: flex;
  flex-direction: column;
  gap: 2px;
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
</style>
