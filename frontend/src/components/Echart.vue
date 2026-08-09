<template>
  <div ref="chartRef" class="echart-container" :style="{ width, height }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import echarts from '@/utils/echarts'

const props = defineProps({
  options: { type: Object, required: true },
  width: { type: String, default: '100%' },
  height: { type: String, default: '400px' },
  autoResize: { type: Boolean, default: true },
  clickable: { type: Boolean, default: true }
})

const emit = defineEmits(['click', 'dblclick'])

const chartRef = ref(null)
let chartInstance = null
let resizeObserver = null

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(props.options, true)

  if (props.clickable) {
    chartInstance.on('click', (params) => emit('click', params))
    chartInstance.on('dblclick', (params) => emit('dblclick', params))
  }
}

function resize() {
  if (chartInstance && chartRef.value) {
    const w = chartRef.value.offsetWidth
    if (w > 0) {
      chartInstance.resize()
    }
  }
}

function startResizeObserver() {
  if (typeof ResizeObserver === 'undefined' || !chartRef.value) return
  resizeObserver = new ResizeObserver(() => {
    if (chartRef.value && chartRef.value.offsetWidth > 0) {
      resize()
    }
  })
  resizeObserver.observe(chartRef.value)
}

onMounted(() => {
  nextTick(() => {
    initChart()
    if (props.autoResize) {
      window.addEventListener('resize', resize)
      startResizeObserver()
    }
  })
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  chartInstance?.dispose()
  window.removeEventListener('resize', resize)
})

watch(() => props.options, (newOptions) => {
  chartInstance?.setOption(newOptions, true)
}, { deep: true })

defineExpose({
  resize,
  getInstance: () => chartInstance
})
</script>

<style scoped>
.echart-container {
  min-height: 300px;
}
</style>