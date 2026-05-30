<template>
  <el-card>
    <div class="stat-card">
      <div class="stat-value" :style="{ color: color }">{{ displayValue }}<span v-if="suffix" class="stat-suffix">{{ suffix }}</span></div>
      <div class="stat-label">{{ label }}</div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  label: { type: String, default: '' },
  color: { type: String, default: '#409EFF' },
  suffix: { type: String, default: '' },
  decimal: { type: Number, default: 0 },
})

const displayValue = computed(() => {
  if (props.decimal > 0) return props.value.toFixed(props.decimal)
  return props.value
})
</script>

<style scoped>
.stat-card { text-align: center; padding: 12px 0; }
.stat-value { font-size: 26px; font-weight: bold; line-height: 1.2; }
.stat-suffix { font-size: 14px; font-weight: normal; margin-left: 2px; }
.stat-label { font-size: 13px; color: #999; margin-top: 6px; }
</style>