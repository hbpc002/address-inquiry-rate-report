<template>
  <div
    class="agent-step"
    :class="['is-' + status, 'kind-' + kind]"
    :role="canExpand ? 'button' : undefined"
    :tabindex="canExpand ? 0 : undefined"
    @click="toggle"
    @keydown.enter.prevent="toggle"
    @keydown.space.prevent="toggle"
  >
    <span class="step-mark" aria-hidden="true">
      <span v-if="running" class="step-spinner"></span>
      <span v-else>{{ mark }}</span>
    </span>

    <div class="step-main">
      <div class="step-line">
        <span class="step-label">{{ label }}</span>
        <span v-if="subject" class="step-subject">{{ subject }}</span>
        <span v-if="meta" class="step-meta">{{ meta }}</span>
        <span v-if="canExpand" class="step-chevron" :class="{ open: expanded }">›</span>
      </div>
      <div v-if="expanded" class="step-detail" @click.stop>
        <template v-if="kind === 'thinking'">
          <pre>{{ step.thinkContent || step.title }}</pre>
        </template>
        <template v-else>
          <div v-if="step.input != null" class="detail-block">
            <div class="detail-title">入参</div>
            <pre>{{ pretty(step.input) }}</pre>
          </div>
          <div v-if="step.error" class="detail-block">
            <div class="detail-title">错误</div>
            <pre class="detail-error">{{ step.error }}</pre>
          </div>
          <div v-else-if="step.output" class="detail-block">
            <div class="detail-title">结果</div>
            <pre>{{ pretty(step.output) }}</pre>
          </div>
          <div v-if="!step.input && !step.output && !step.error" class="detail-empty">暂无详情</div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  step: { type: Object, required: true },
})

const expanded = ref(false)

const status = computed(() => props.step.status || 'loading')
const running = computed(() => status.value === 'loading')
const kind = computed(() => props.step.kind || (props.step.toolName ? 'tool' : 'status'))
const label = computed(() => props.step.title || props.step.toolName || '步骤')

const subject = computed(() => {
  if (props.step.subject) return props.step.subject
  if (kind.value === 'thinking' && running.value) return props.step.thinkContent || ''
  return ''
})

const mark = computed(() => {
  if (status.value === 'success') return '✓'
  if (status.value === 'error') return '×'
  if (status.value === 'stopped') return '–'
  return '•'
})

const meta = computed(() => {
  if (running.value) return '执行中'
  const parts = []
  if (props.step.outcome) parts.push(props.step.outcome)
  if (props.step.durationMs != null) parts.push(formatDuration(props.step.durationMs))
  return parts.join(' · ')
})

const canExpand = computed(() => {
  if (kind.value === 'thinking') return !!(props.step.thinkContent || props.step.title)
  return !!(props.step.input != null || props.step.output || props.step.error)
})

function formatDuration(ms) {
  if (ms == null || Number.isNaN(ms)) return ''
  if (ms < 1000) return `${Math.max(0, Math.round(ms))}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m${Math.round(seconds % 60)}s`
}

function pretty(value) {
  if (value == null) return ''
  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2)
    } catch (e) {
      return value
    }
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch (e) {
    return String(value)
  }
}

function toggle() {
  if (canExpand.value) expanded.value = !expanded.value
}
</script>

<style scoped>
.agent-step {
  position: relative;
  padding: 4px 6px 4px 26px;
  border-radius: 6px;
  outline: none;
  transition: background-color 0.15s ease;
}
.agent-step[role='button'] {
  cursor: pointer;
}
.agent-step[role='button']:hover {
  background: #f5f7fa;
}
.agent-step:focus-visible {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.25);
}
.step-mark {
  position: absolute;
  left: 0;
  top: 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  color: #909399;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  z-index: 1;
}
.is-success .step-mark {
  color: #67c23a;
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
}
.is-error .step-mark {
  color: #f56c6c;
  background: #fef0f0;
  border: 1px solid #fbc4c4;
}
.is-stopped .step-mark {
  color: #909399;
  background: #f4f4f5;
  border: 1px solid #d3d4d6;
}
.is-loading .step-mark {
  color: #409eff;
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
}
.kind-thinking .step-mark {
  color: #8e6bd8;
  background: #f4f0fb;
  border-color: #d9c9f5;
}
.step-main {
  min-width: 0;
}
.step-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-height: 20px;
  font-size: 13px;
  color: #303133;
}
.step-label {
  font-weight: 600;
  flex-shrink: 0;
  max-width: 45%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.step-subject {
  color: #606266;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}
.step-meta {
  margin-left: auto;
  color: #909399;
  font-size: 11px;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}
.is-error .step-meta {
  color: #f56c6c;
}
.step-chevron {
  color: #c0c4cc;
  font-size: 15px;
  line-height: 1;
  flex-shrink: 0;
  transition: transform 0.18s ease;
  transform: rotate(90deg);
}
.step-chevron.open {
  transform: rotate(-90deg);
}
.step-detail {
  margin: 6px 0 2px;
  padding: 8px 10px;
  background: #f7f8fa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}
.detail-block + .detail-block {
  margin-top: 8px;
}
.detail-title {
  margin-bottom: 3px;
  color: #909399;
  font-size: 11px;
  font-weight: 600;
}
.step-detail pre {
  margin: 0;
  max-height: 240px;
  overflow: auto;
  color: #4b5563;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.step-detail pre.detail-error {
  color: #f56c6c;
}
.detail-empty {
  color: #909399;
  font-size: 12px;
}
.step-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid #b3d8ff;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: agent-step-spin 0.8s linear infinite;
}
@keyframes agent-step-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
