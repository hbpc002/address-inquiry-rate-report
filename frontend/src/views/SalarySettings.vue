<template>
  <div class="salary-settings">
    <el-card>
      <template #header><span>绩效工资配置</span></template>

      <el-form label-width="160px" v-loading="loading">
        <el-divider content-position="left">接话绩效工资 - 梯度</el-divider>
        <el-table :data="callTiers" size="small" border stripe max-height="300">
          <el-table-column label="序号" width="60" type="index" />
          <el-table-column label="最低次数" width="120">
            <template #default="{ row }">{{ row.min }}</template>
          </el-table-column>
          <el-table-column label="最高次数" width="120">
            <template #default="{ row }">{{ row.max === null ? '不限' : row.max }}</template>
          </el-table-column>
          <el-table-column label="单价" width="120">
            <template #default="{ row }">
              <el-input-number v-model="row.rate" :min="0" :max="10" :step="0.1" size="small" />
            </template>
          </el-table-column>
        </el-table>

        <el-divider content-position="left">满意度绩效工资</el-divider>
        <el-form-item label="满意度字段">
          <el-input v-model="satSalary.field_e" disabled size="small" />
        </el-form-item>
        <el-form-item label="权重字段">
          <el-input v-model="satSalary.field_f" disabled size="small" />
        </el-form-item>
        <el-form-item label="系数">
          <el-input-number v-model="satSalary.coefficient" :min="0" :max="10" :step="0.1" size="small" />
        </el-form-item>

        <el-divider content-position="left">话务量差额目标值</el-divider>
        <el-form-item label="目标值">
          <el-select v-model="callGapTargets" multiple allow-create filterable default-first-option
            placeholder="输入目标值后回车" size="small" style="width: 400px" />
        </el-form-item>

        <el-divider content-position="left">满意度差额系数</el-divider>
        <el-form-item label="系数 A（全部×A）">
          <el-input-number v-model="satDiff.coeff_a" :min="0" :max="100" size="small" />
        </el-form-item>
        <el-form-item label="系数 B（部分×B）">
          <el-input-number v-model="satDiff.coeff_b" :min="0" :max="100" size="small" />
        </el-form-item>
        <p class="formula-hint">
          公式：满意度差额 = (E+F+G+H+I) × {{ satDiff.coeff_a }} - (E+F) × {{ satDiff.coeff_b }}
        </p>

        <el-divider content-position="left">指标预警配置</el-divider>
        <div style="margin-bottom: 12px">
          <el-button type="primary" size="small" @click="openAddTarget">添加规则</el-button>
        </div>
        <el-table :data="metricTargets" size="small" border stripe max-height="300">
          <el-table-column label="启用" width="60" align="center">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="指标名称" min-width="120">
            <template #default="{ row }">{{ row.label }}</template>
          </el-table-column>
          <el-table-column label="字段" min-width="180">
            <template #default="{ row }">
              <code style="font-size: 12px; color: #909399">{{ row.field }}</code>
            </template>
          </el-table-column>
          <el-table-column label="条件" width="70" align="center">
            <template #default="{ row }">
              {{ operatorLabel(row.operator) }}
            </template>
          </el-table-column>
          <el-table-column label="目标值" width="90" align="center">
            <template #default="{ row }">{{ row.value }}</template>
          </el-table-column>
          <el-table-column label="预警颜色" width="80" align="center">
            <template #default="{ row }">
              <span :style="{ display: 'inline-block', width: '20px', height: '20px', borderRadius: '4px', backgroundColor: row.color, verticalAlign: 'middle' }" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center">
            <template #default="{ row, $index }">
              <el-button type="primary" link size="small" @click="openEditTarget($index)">编辑</el-button>
              <el-button type="danger" link size="small" @click="deleteTarget($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-form-item style="margin-top: 16px">
          <el-button type="primary" @click="saveConfig" :loading="saving">保存配置</el-button>
          <el-button @click="resetConfig">重置为默认</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="targetDialogVisible" :title="targetDialogTitle" width="500px">
      <el-form :model="targetForm" label-width="100px" size="small">
        <el-form-item label="指标名称">
          <el-input v-model="targetForm.label" placeholder="例如：满意率" />
        </el-form-item>
        <el-form-item label="字段">
          <el-input v-model="targetForm.field" placeholder="例如：_ti_dan_lv" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            常用字段：<code>人工服务-满意度-满意率</code>（满意率）、<code>_ti_dan_lv</code>（提单率）
          </div>
        </el-form-item>
        <el-form-item label="条件">
          <el-select v-model="targetForm.operator" style="width: 120px">
            <el-option label="<" value="lt" />
            <el-option label="<=" value="le" />
            <el-option label=">" value="gt" />
            <el-option label=">=" value="ge" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标值">
          <el-input-number v-model="targetForm.value" :min="0" :max="99999" :step="0.01" :precision="4" />
        </el-form-item>
        <el-form-item label="预警颜色">
          <el-color-picker v-model="targetForm.color" show-alpha />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="targetForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="targetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmTarget">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const saving = ref(false)

const DEFAULT_CALL_TIERS = [
  { min: 0, max: 1000, rate: 1.0 },
  { min: 1000, max: 2000, rate: 1.5 },
  { min: 2000, max: 3500, rate: 1.2 },
  { min: 3500, max: null, rate: 1.0 }
]

const DEFAULT_METRIC_TARGETS = [
  { field: '人工服务-满意度-满意率', label: '满意率', operator: 'lt', value: 0.95, color: '#F56C6C', enabled: true },
  { field: '_ti_dan_lv', label: '提单率', operator: 'gt', value: 0.15, color: '#F56C6C', enabled: true }
]

const callTiers = ref(JSON.parse(JSON.stringify(DEFAULT_CALL_TIERS)))
const satSalary = reactive({
  field_e: '',
  field_f: '',
  coefficient: 0.5
})
const callGapTargets = ref([2000, 2500, 3000])
const satDiff = reactive({
  coeff_a: 19,
  coeff_b: 20
})
const metricTargets = ref([])

const targetDialogVisible = ref(false)
const editingTargetIndex = ref(-1)
const targetForm = reactive({
  field: '',
  label: '',
  operator: 'lt',
  value: 0,
  color: '#F56C6C',
  enabled: true
})

const targetDialogTitle = computed(() => editingTargetIndex.value >= 0 ? '编辑预警规则' : '添加预警规则')

function operatorLabel(op) {
  const map = { lt: '<', le: '<=', gt: '>', ge: '>=' }
  return map[op] || op
}

function openAddTarget() {
  editingTargetIndex.value = -1
  targetForm.field = ''
  targetForm.label = ''
  targetForm.operator = 'lt'
  targetForm.value = 0
  targetForm.color = '#F56C6C'
  targetForm.enabled = true
  targetDialogVisible.value = true
}

function openEditTarget(index) {
  const t = metricTargets.value[index]
  editingTargetIndex.value = index
  targetForm.field = t.field
  targetForm.label = t.label
  targetForm.operator = t.operator
  targetForm.value = t.value
  targetForm.color = t.color
  targetForm.enabled = t.enabled
  targetDialogVisible.value = true
}

function confirmTarget() {
  if (!targetForm.field || !targetForm.label) {
    ElMessage.warning('请填写指标名称和字段')
    return
  }
  const data = {
    field: targetForm.field,
    label: targetForm.label,
    operator: targetForm.operator,
    value: targetForm.value,
    color: targetForm.color,
    enabled: targetForm.enabled
  }
  if (editingTargetIndex.value >= 0) {
    metricTargets.value[editingTargetIndex.value] = data
  } else {
    metricTargets.value.push(data)
  }
  targetDialogVisible.value = false
}

async function deleteTarget(index) {
  try {
    await ElMessageBox.confirm('确定要删除该预警规则吗？', '确认删除', { type: 'warning' })
    metricTargets.value.splice(index, 1)
  } catch { /* cancelled */ }
}

async function loadConfig() {
  loading.value = true
  try {
    const res = await api.get('/salary-config')
    const items = res.data.items || []
    for (const item of items) {
      if (item.rule_key === 'call_salary_tiers') {
        callTiers.value = item.rule_data.tiers || JSON.parse(JSON.stringify(DEFAULT_CALL_TIERS))
      } else if (item.rule_key === 'sat_salary') {
        Object.assign(satSalary, item.rule_data)
      } else if (item.rule_key === 'call_gap_targets') {
        callGapTargets.value = item.rule_data.targets || [2000, 2500, 3000]
      } else if (item.rule_key === 'sat_diff') {
        satDiff.coeff_a = item.rule_data.coeff_a ?? 19
        satDiff.coeff_b = item.rule_data.coeff_b ?? 20
      } else if (item.rule_key === 'metric_targets') {
        metricTargets.value = item.rule_data.targets || []
      }
    }
  } catch {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

function getDefaults() {
  return {
    callTiers: JSON.parse(JSON.stringify(DEFAULT_CALL_TIERS)),
    satSalary: { field_e: '呼入人工服务-满意度-非常满意量', field_f: '呼入人工服务-满意度-满意量', coefficient: 0.5 },
    callGapTargets: [2000, 2500, 3000],
    satDiff: { coeff_a: 19, coeff_b: 20 }
  }
}

function resetConfig() {
  const def = getDefaults()
  callTiers.value = def.callTiers
  Object.assign(satSalary, def.satSalary)
  callGapTargets.value = def.callGapTargets
  satDiff.coeff_a = def.satDiff.coeff_a
  satDiff.coeff_b = def.satDiff.coeff_b
  metricTargets.value = JSON.parse(JSON.stringify(DEFAULT_METRIC_TARGETS))
  ElMessage.info('已重置为默认值，点击"保存配置"生效')
}

async function saveConfig() {
  saving.value = true
  try {
    await api.put('/salary-config/call_salary_tiers', { rule_data: { tiers: callTiers.value } })
    await api.put('/salary-config/sat_salary', { rule_data: { ...satSalary } })
    await api.put('/salary-config/call_gap_targets', { rule_data: { targets: callGapTargets.value.map(Number) } })
    await api.put('/salary-config/sat_diff', { rule_data: { coeff_a: satDiff.coeff_a, coeff_b: satDiff.coeff_b } })
    await api.put('/salary-config/metric_targets', { rule_data: { targets: metricTargets.value } })
    ElMessage.success('配置已保存')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.salary-settings {
  max-width: 960px;
  margin: 0 auto;
}
.formula-hint {
  font-size: 13px;
  color: #909399;
  margin: -10px 0 10px 160px;
}
</style>
