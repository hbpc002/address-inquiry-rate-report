<template>
  <el-table-column v-bind="$attrs">
    <template #header>
      <span class="column-header">{{ label }}</span>
      <el-tooltip v-if="hasContent" placement="top" :width="360">
        <template #content>
          <div class="annotation-tip">
            <div v-if="annotation?.source" class="tip-section">
              <div class="tip-label">数据来源</div>
              <div class="tip-text">{{ annotation.source }}</div>
            </div>
            <div v-if="annotation?.formula" class="tip-section">
              <div class="tip-label">计算公式</div>
              <div class="tip-text">{{ annotation.formula }}</div>
            </div>
            <div v-if="annotation?.description" class="tip-section">
              <div class="tip-label">口径说明</div>
              <div class="tip-text">{{ annotation.description }}</div>
            </div>
          </div>
        </template>
        <span class="tip-icon">ⓘ</span>
      </el-tooltip>
    </template>
    <template #default="scope">
      <slot name="default" v-bind="scope">
        {{ scope.row[prop] }}
      </slot>
    </template>
  </el-table-column>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  prop: { type: String, default: '' },
  annotation: { type: Object, default: null },
})

const hasContent = computed(() => {
  if (!props.annotation) return false
  return !!(props.annotation.source || props.annotation.formula || props.annotation.description)
})
</script>

<style scoped>
.column-header {
  display: inline-block;
}
.annotation-tip {
  line-height: 1.6;
}
.tip-section {
  margin-bottom: 6px;
}
.tip-section:last-child {
  margin-bottom: 0;
}
.tip-label {
  font-weight: 600;
  color: #409eff;
  font-size: 12px;
  margin-bottom: 2px;
}
.tip-text {
  color: #303133;
  font-size: 13px;
  white-space: pre-line;
}
.tip-icon {
  color: #909399;
  cursor: help;
  font-size: 14px;
  margin-left: 2px;
}
</style>
