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

        <el-form-item>
          <el-button type="primary" @click="saveConfig" :loading="saving">保存配置</el-button>
          <el-button @click="resetConfig">重置为默认</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const saving = ref(false)

const DEFAULT_CALL_TIERS = [
  { min: 0, max: 1000, rate: 1.0 },
  { min: 1000, max: 2000, rate: 1.5 },
  { min: 2000, max: 3500, rate: 1.2 },
  { min: 3500, max: null, rate: 1.0 }
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

const ORIGINAL = { callTiers: null, satSalary: null, callGapTargets: null, satDiff: null }

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
  ElMessage.info('已重置为默认值，点击"保存配置"生效')
}

async function saveConfig() {
  saving.value = true
  try {
    await api.put('/salary-config/call_salary_tiers', { rule_data: { tiers: callTiers.value } })
    await api.put('/salary-config/sat_salary', { rule_data: { ...satSalary } })
    await api.put('/salary-config/call_gap_targets', { rule_data: { targets: callGapTargets.value.map(Number) } })
    await api.put('/salary-config/sat_diff', { rule_data: { coeff_a: satDiff.coeff_a, coeff_b: satDiff.coeff_b } })
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
  max-width: 800px;
  margin: 0 auto;
}
.formula-hint {
  font-size: 13px;
  color: #909399;
  margin: -10px 0 10px 160px;
}
</style>
