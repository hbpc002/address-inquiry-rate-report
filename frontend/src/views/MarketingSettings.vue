<template>
  <div class="marketing-settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.marketing_settings }}</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="总体营销行分类规则同时用于总体营销表和营销统计的“行分类”。线上直办数据命中“线上直办-*”，办理工单数据先按线上直办组织机构分类、未命中再按“建单租户”分类，归入“营销工单-*”。按优先级从小到大匹配，第一条命中生效。"
        style="margin-bottom: 12px"
      />
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="正则匹配提示"
        style="margin-bottom: 16px"
      >
        <template #default>
          匹配方式选择“正则”时，匹配内容需填写正则表达式，例如：<code>热线|营销</code>、<code>^广西.*分公司$</code>；支持
          <code>\d</code>、<code>.*</code>、<code>|</code>、<code>[]</code> 等常用语法，匹配不区分大小写。
        </template>
      </el-alert>

      <el-form inline>
        <el-form-item>
          <el-button type="primary" @click="addRule">新增规则</el-button>
          <el-button type="success" :loading="saving" @click="saveRules">保存</el-button>
        </el-form-item>
        <el-form-item label="未分类产品行">
          <el-tag type="warning">{{ preview.unclassified }}</el-tag>
        </el-form-item>
      </el-form>

      <el-table :data="config.rules" border stripe max-height="360">
        <el-table-column label="启用" width="70" align="center">
          <template #default="{ row }"><el-switch v-model="row.enabled" size="small" /></template>
        </el-table-column>
        <el-table-column label="归入行" min-width="170">
          <template #default="{ row }">
            <el-select v-model="row.row_label" filterable style="width: 100%">
              <el-option v-for="label in ROW_LABELS" :key="label" :label="label" :value="label" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="匹配字段" width="170">
          <template #default="{ row }">
            <el-select v-model="row.field" style="width: 100%">
              <el-option v-for="item in OVERALL_FIELDS" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="匹配方式" width="140">
          <template #default="{ row }">
            <el-select v-model="row.match_type" style="width: 100%">
              <el-option v-for="item in MATCH_TYPES" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="匹配内容" min-width="220">
          <template #default="{ row }">
            <el-input v-model="row.pattern" :placeholder="patternPlaceholder(row)" />
            <div v-if="row.match_type === 'regex'" class="regex-hint">正则例：热线|营销</div>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="110">
          <template #default="{ row }"><el-input-number v-model="row.priority" :min="0" :max="9999" size="small" /></template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ $index }">
            <el-button type="danger" link @click="config.rules.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider content-position="left">组织机构命中行分类预览</el-divider>
      <el-table :data="organizations" border stripe max-height="320">
        <el-table-column prop="source" label="数据来源" width="100" />
        <el-table-column prop="org_name" label="组织机构/建单租户" min-width="420" show-overflow-tooltip />
        <el-table-column prop="count" label="明细行数" width="100" />
        <el-table-column prop="row_label" label="命中行分类" width="160" />
      </el-table>

      <el-divider content-position="left">未分类取值预览</el-divider>
      <el-table :data="preview.samples" border stripe max-height="300">
        <el-table-column prop="field" label="字段" width="180" />
        <el-table-column prop="value" label="取值" min-width="360" show-overflow-tooltip />
        <el-table-column prop="count" label="行数" width="90" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage } from 'element-plus'

const ui = useUiConfigStore()
const saving = ref(false)
const config = reactive({ rules: [] })
const organizations = ref([])
const preview = reactive({ unclassified: 0, samples: [] })

const MATCH_TYPES = [
  { value: 'contains', label: '包含' },
  { value: 'equals', label: '等于' },
  { value: 'prefix', label: '前缀' },
  { value: 'suffix', label: '后缀' },
  { value: 'regex', label: '正则（表达式）' }
]

const ROW_LABELS = [
  '线上直办-热线', '线上直办-区域', '线上直办-维系', '线上直办-工单', '线上直办-分公司',
  '营销工单-热线', '营销工单-区域', '营销工单-维系', '营销工单-工单', '营销工单-分公司',
  '降套维系'
]

const OVERALL_FIELDS = [
  { value: 'org_name', label: '组织机构' },
  { value: 'tenant', label: '建单租户' },
  { value: 'channel', label: '受理渠道' },
  { value: 'pos_sequence', label: '人员岗位性质' },
  { value: 'develop_depart_name', label: '发展渠道' },
  { value: 'service_type', label: '重点业务分类' },
  { value: 'data_type', label: '数据类型' },
  { value: 'area_name', label: '地市' },
  { value: 'tb_region_name', label: '通报区域' }
]

function patternPlaceholder(row) {
  return row.match_type === 'regex' ? '正则表达式，如：热线|营销' : '如：热线运营组'
}

function addRule() {
  config.rules.push({
    id: '',
    row_label: '线上直办-热线',
    field: 'org_name',
    match_type: 'contains',
    pattern: '',
    priority: 10,
    enabled: true
  })
}

async function loadRules() {
  const res = await api.get('/marketing/overall-row-rules')
  config.rules = res.data.rules || []
}

async function loadPreviews() {
  try {
    const [orgRes, previewRes] = await Promise.all([
      api.get('/marketing/organizations'),
      api.get('/marketing/row-rule-preview')
    ])
    organizations.value = orgRes.data.items || []
    preview.unclassified = previewRes.data.unclassified || 0
    preview.samples = previewRes.data.samples || []
  } catch (e) {
    /* 预览失败不影响规则编辑 */
  }
}

async function saveRules() {
  saving.value = true
  try {
    await api.put('/marketing/overall-row-rules', { rules: config.rules })
    ElMessage.success('总体营销行分类规则已保存')
    await loadRules()
    await loadPreviews()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadRules()
    await loadPreviews()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.regex-hint {
  margin-top: 2px;
  color: #909399;
  font-size: 12px;
  line-height: 1.4;
}
</style>
