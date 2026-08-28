<template>
  <div v-if="visible">
    <button
      class="agent-fab"
      :style="fabStyle"
      @click="open = true"
      :title="config.label"
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
import { ref, computed, onMounted } from 'vue'
import { api } from '@/stores/user'
import { useUserStore } from '@/stores/user'
import AgentChat from '@/views/AgentChat.vue'

const userStore = useUserStore()
const open = ref(false)
const config = ref({
  enabled: true, label: '智能助手', icon_type: 'emoji', icon_value: '🤖', position: 'bottom-right', color: '#409EFF',
})

const visible = computed(() => config.value.enabled && userStore.hasPermission('agent.use'))

const fabStyle = computed(() => {
  const pos = config.value.position === 'bottom-left'
    ? { left: '24px', bottom: '24px' }
    : { right: '24px', bottom: '24px' }
  return { ...pos, background: config.value.color || '#409EFF' }
})

async function loadConfig() {
  try {
    const r = await api.get('/llm-providers/launcher')
    if (r.data) config.value = { ...config.value, ...r.data }
  } catch (e) { /* 使用默认配置 */ }
}

onMounted(loadConfig)
</script>

<style scoped>
.agent-fab {
  position: fixed;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  color: #fff;
}
.fab-emoji { font-size: 26px; line-height: 1; }
.fab-icon { width: 30px; height: 30px; object-fit: contain; }
.fab-icon :deep(svg) { width: 30px; height: 30px; fill: #fff; }
</style>
