<template>
  <div class="chart-panel" :class="{ 'is-fullscreen': isFullscreen }">
    <div class="chart-header" v-if="title || $slots.tools">
      <span class="chart-title">{{ title }}</span>
      <div class="chart-tools">
        <slot name="tools"></slot>
        <el-button v-if="fullscreenable" :icon="FullScreen" circle size="small" @click="toggleFullscreen" />
      </div>
    </div>
    <div class="chart-body">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { FullScreen } from '@element-plus/icons-vue'

const props = defineProps({
  title: { type: String, default: '' },
  fullscreenable: { type: Boolean, default: true }
})

const isFullscreen = ref(false)

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  if (isFullscreen.value) {
    document.addEventListener('keydown', handleEsc)
  } else {
    document.removeEventListener('keydown', handleEsc)
  }
}

function handleEsc(e) {
  if (e.key === 'Escape' && isFullscreen.value) {
    isFullscreen.value = false
    document.removeEventListener('keydown', handleEsc)
  }
}

defineExpose({ isFullscreen, toggleFullscreen })
</script>

<style scoped>
.chart-panel {
  background: #fff;
  border-radius: 4px;
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chart-panel.is-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2000;
  background: #fff;
  padding: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chart-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.chart-tools {
  display: flex;
  gap: 8px;
  align-items: center;
}

.chart-body {
  flex: 1;
  min-height: 0;
}

.is-fullscreen .chart-body {
  height: calc(100% - 50px);
}
</style>