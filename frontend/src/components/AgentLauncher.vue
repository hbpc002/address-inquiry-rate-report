<template>
  <div v-if="visible">
    <button
      ref="fabEl"
      class="agent-fab"
      :style="fabStyle"
      :title="config.label"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
    >
      <img v-if="config.icon_type === 'url'" :src="config.icon_value" alt="" class="fab-icon" />
      <span v-else-if="config.icon_type === 'svg'" v-html="config.icon_value" class="fab-icon"></span>
      <span v-else class="fab-emoji">{{ config.icon_value }}</span>
    </button>

    <el-drawer v-model="open" :title="config.label || '智能助手'" direction="rtl" size="480px">
      <AgentChat embedded />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { api } from '@/stores/user'
import { useUserStore } from '@/stores/user'
import { useLauncherStore } from '@/stores/launcher'

const AgentChat = defineAsyncComponent(() => import('@/views/AgentChat.vue'))

const userStore = useUserStore()
const launcher = useLauncherStore()
const open = ref(false)
const fabEl = ref(null)

const config = computed(() => launcher.config)
const pos = computed(() => launcher.pos)

const visible = computed(() => config.value.enabled && userStore.hasPermission('agent.use'))

const fabStyle = computed(() => {
  if (pos.value.left != null) {
    return { left: pos.value.left + 'px', top: pos.value.top + 'px', background: config.value.color || '#409EFF' }
  }
  const base = { background: config.value.color || '#409EFF' }
  return config.value.position === 'bottom-left'
    ? { left: '24px', bottom: '24px', ...base }
    : { right: '24px', bottom: '24px', ...base }
})

let dragging = false
let moved = false
let startX = 0
let startY = 0
let origLeft = 0
let origTop = 0

function onPointerDown(e) {
  if (!config.value.draggable) {
    open.value = true
    return
  }
  const rect = fabEl.value.getBoundingClientRect()
  dragging = true
  moved = false
  startX = e.clientX
  startY = e.clientY
  origLeft = rect.left
  origTop = rect.top
  fabEl.value.setPointerCapture(e.pointerId)
}

function onPointerMove(e) {
  if (!dragging) return
  const dx = e.clientX - startX
  const dy = e.clientY - startY
  if (Math.abs(dx) > 4 || Math.abs(dy) > 4) moved = true
  let left = origLeft + dx
  let top = origTop + dy
  left = Math.max(0, Math.min(left, window.innerWidth - 56))
  top = Math.max(0, Math.min(top, window.innerHeight - 56))
  launcher.setPos(left, top)
}

async function onPointerUp(e) {
  if (!dragging) return
  dragging = false
  try { fabEl.value.releasePointerCapture(e.pointerId) } catch (_) {}
  if (moved) {
    await persistPos()
  } else {
    open.value = true
  }
}

async function persistPos() {
  try {
    await api.put('/llm-providers/launcher', { pos_x: Math.round(pos.value.left), pos_y: Math.round(pos.value.top) })
  } catch (_) { /* 忽略保存失败 */ }
}

onMounted(() => launcher.load())
</script>

<style scoped>
.agent-fab {
  position: fixed;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  cursor: grab;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  color: #fff;
  touch-action: none;
  user-select: none;
}
.agent-fab:active { cursor: grabbing; }
.fab-emoji { font-size: 26px; line-height: 1; }
.fab-icon { width: 30px; height: 30px; object-fit: contain; }
.fab-icon :deep(svg) { width: 30px; height: 30px; fill: #fff; }
</style>
