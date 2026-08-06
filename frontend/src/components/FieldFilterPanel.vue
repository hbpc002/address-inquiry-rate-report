<template>
  <div class="field-filter-panel">
    <el-popover
      trigger="click"
      width="500"
      v-model:visible="visible"
    >
      <template #reference>
        <el-button size="small" :type="activeCount > 0 ? 'primary' : 'default'" :loading="loading">
          字段筛选
          <el-badge v-if="activeCount > 0" :value="activeCount" class="filter-badge" type="danger" />
        </el-button>
      </template>

      <div class="filter-body">
        <div v-if="!fields.length" class="filter-empty">暂无可用字段</div>

        <div v-for="(cond, index) in localConditions" :key="cond._id" class="filter-row">
          <el-select v-model="cond.fieldKey" size="small" placeholder="选择字段" filterable style="width: 200px" :teleported="false" @change="syncUnit(cond)">
            <el-option v-for="f in fields" :key="f.key" :label="f.label" :value="f.key" />
          </el-select>
          <el-select v-model="cond.operator" size="small" style="width: 100px" :teleported="false">
            <el-option label="大于" value="gt" />
            <el-option label="大于等于" value="ge" />
            <el-option label="小于" value="lt" />
            <el-option label="小于等于" value="le" />
          </el-select>
          <el-input-number
            v-model="cond.value"
            size="small"
            :controls="false"
            :precision="2"
            :step="0.1"
            :min="cond.unit === 'percent' ? 0 : undefined"
            style="width: 110px"
          />
          <span v-if="cond.unit === 'percent'" class="unit">%</span>
          <el-button type="danger" link size="small" @click="removeCondition(index)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>

        <div class="filter-actions">
          <el-button size="small" @click="addCondition" :disabled="!fields.length">
            <el-icon style="margin-right: 2px"><Plus /></el-icon>添加条件
          </el-button>
          <el-button v-if="localConditions.length" size="small" type="danger" plain @click="clear">清空</el-button>
        </div>
      </div>

      <div class="filter-footer">
        <el-button size="small" @click="visible = false">取消</el-button>
        <el-button size="small" type="primary" @click="confirm">应用</el-button>
      </div>
    </el-popover>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'

const props = defineProps({
  fields: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  persistKey: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'change'])

let idCounter = 0
const localConditions = ref([])
const visible = ref(false)

function getField(key) {
  return props.fields.find(f => f.key === key)
}

function syncUnit(cond) {
  const f = getField(cond.fieldKey)
  cond.unit = f ? f.unit : 'number'
}

watch(() => props.modelValue, (val) => {
  localConditions.value = (val || []).map(c => {
    idCounter += 1
    const f = getField(c.fieldKey)
    return { _id: idCounter, fieldKey: c.fieldKey, operator: c.operator || 'gt', value: c.value ?? null, unit: f ? f.unit : (c.unit || 'number') }
  })
}, { immediate: true, deep: true })

const activeCount = computed(() =>
  localConditions.value.filter(c => c.fieldKey && c.value !== null && c.value !== undefined && c.value !== '').length
)

function addCondition() {
  const firstField = props.fields[0]
  idCounter += 1
  localConditions.value.push({
    _id: idCounter,
    fieldKey: firstField ? firstField.key : '',
    operator: 'gt',
    value: null,
    unit: firstField ? firstField.unit : 'number'
  })
}

function removeCondition(index) {
  localConditions.value.splice(index, 1)
}

function clear() {
  localConditions.value = []
  emit('update:modelValue', [])
  emit('change', [])
  if (props.persistKey) {
    try { sessionStorage.removeItem(props.persistKey) } catch { /* ignore */ }
  }
}

function confirm() {
  const cleaned = localConditions.value
    .filter(c => c.fieldKey && c.value !== null && c.value !== undefined && c.value !== '')
    .map(c => {
      const f = getField(c.fieldKey)
      return { fieldKey: c.fieldKey, operator: c.operator, value: c.value, unit: f ? f.unit : (c.unit || 'number') }
    })
  emit('update:modelValue', cleaned)
  emit('change', cleaned)
  visible.value = false
}
</script>

<style scoped>
.filter-badge {
  margin-left: 6px;
  vertical-align: middle;
}
.filter-body {
  max-height: 320px;
  overflow-y: auto;
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.filter-row .unit {
  color: #909399;
  font-size: 12px;
}
.filter-actions {
  margin-top: 4px;
}
.filter-empty {
  color: #909399;
  padding: 12px 0;
  text-align: center;
}
.filter-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}
</style>