<template>
  <div class="marketing-settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.marketing_settings }}</span>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="组织分组规则" name="group">
          <el-alert
            type="info"
            :closable="false"
            title="用于营销统计中的“自定义分组”筛选和员工维度展示。按优先级从小到大匹配，第一条命中生效；未命中归入默认分组。"
            style="margin-bottom: 12px"
          />
          <el-form inline>
            <el-form-item label="默认分组">
              <el-input v-model="groupConfig.default_group" placeholder="未分组" style="width: 180px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="addGroupRule">新增规则</el-button>
              <el-button type="success" :loading="savingGroup" @click="saveGroupRules">保存</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="groupConfig.rules" border stripe>
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }"><el-switch v-model="row.enabled" size="small" /></template>
            </el-table-column>
            <el-table-column label="目标分组" min-width="150">
              <template #default="{ row }"><el-input v-model="row.group_name" placeholder="如：维系组" /></template>
            </el-table-column>
            <el-table-column label="匹配方式" width="130">
              <template #default="{ row }">
                <el-select v-model="row.match_type" style="width: 100%">
                  <el-option v-for="item in MATCH_TYPES" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配内容" min-width="220">
              <template #default="{ row }"><el-input v-model="row.pattern" placeholder="如：维系" /></template>
            </el-table-column>
            <el-table-column label="优先级" width="110">
              <template #default="{ row }"><el-input-number v-model="row.priority" :min="0" :max="9999" size="small" /></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ $index }">
                <el-button type="danger" link @click="groupConfig.rules.splice($index, 1)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider content-position="left">组织命中预览</el-divider>
          <el-table :data="organizations" border stripe max-height="320">
            <el-table-column prop="org_name" label="组织机构（RESERVE6）" min-width="420" show-overflow-tooltip />
            <el-table-column prop="count" label="明细行数" width="100" />
            <el-table-column prop="group_name" label="命中分组" width="140" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="总体营销行分类规则" name="overall">
          <el-alert
            type="info"
            :closable="false"
            title="用于总体营销表：将营销明细归类到线上直办/营销工单的子项、办理工单或降套维系。按优先级第一条命中生效；未命中数据只在表外提示。"
            style="margin-bottom: 12px"
          />
          <el-form inline>
            <el-form-item>
              <el-button type="primary" @click="addOverallRule">新增规则</el-button>
              <el-button type="success" :loading="savingOverall" @click="saveOverallRules">保存</el-button>
            </el-form-item>
            <el-form-item label="未分类产品行">
              <el-tag type="warning">{{ preview.unclassified }}</el-tag>
            </el-form-item>
          </el-form>

          <el-table :data="overallConfig.rules" border stripe max-height="360">
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
            <el-table-column label="匹配方式" width="120">
              <template #default="{ row }">
                <el-select v-model="row.match_type" style="width: 100%">
                  <el-option v-for="item in MATCH_TYPES" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配内容" min-width="200">
              <template #default="{ row }"><el-input v-model="row.pattern" placeholder="如：热线运营组" /></template>
            </el-table-column>
            <el-table-column label="优先级" width="110">
              <template #default="{ row }"><el-input-number v-model="row.priority" :min="0" :max="9999" size="small" /></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ $index }">
                <el-button type="danger" link @click="overallConfig.rules.splice($index, 1)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider content-position="left">未分类取值预览</el-divider>
          <el-table :data="preview.samples" border stripe max-height="300">
            <el-table-column prop="field" label="字段" width="180" />
            <el-table-column prop="value" label="取值" min-width="360" show-overflow-tooltip />
            <el-table-column prop="count" label="行数" width="90" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage } from 'element-plus'

const ui = useUiConfigStore()
const activeTab = ref('group')
const savingGroup = ref(false)
const savingOverall = ref(false)
const groupConfig = reactive({ default_group: '未分组', rules: [] })
const overallConfig = reactive({ rules: [] })
const organizations = ref([])
const preview = reactive({ unclassified: 0, samples: [] })

const MATCH_TYPES = [
  { value: 'contains', label: '包含' },
  { value: 'equals', label: '等于' },
  { value: 'prefix', label: '前缀' },
  { value: 'suffix', label: '后缀' },
  { value: 'regex', label: '正则' }
]

const ROW_LABELS = [
  '线上直办-热线', '线上直办-区域', '线上直办-维系', '线上直办-工单', '线上直办-分公司',
  '办理工单',
  '营销工单-热线', '营销工单-区域', '营销工单-维系', '营销工单-工单', '营销工单-分公司',
  '降套维系'
]

const OVERALL_FIELDS = [
  { value: 'org_name', label: '组织机构 RESERVE6' },
  { value: 'channel', label: '受理渠道' },
  { value: 'pos_sequence', label: '人员岗位性质' },
  { value: 'develop_depart_name', label: '发展渠道' },
  { value: 'service_type', label: '重点业务分类' },
  { value: 'data_type', label: '数据类型' },
  { value: 'area_name', label: '地市' },
  { value: 'tb_region_name', label: '通报区域' }
]

function addGroupRule() {
  groupConfig.rules.push({
    id: '',
    group_name: '',
    match_type: 'contains',
    pattern: '',
    priority: 10,
    enabled: true
  })
}

function addOverallRule() {
  overallConfig.rules.push({
    id: '',
    row_label: '线上直办-热线',
    field: 'org_name',
    match_type: 'contains',
    pattern: '',
    priority: 10,
    enabled: true
  })
}

async function loadGroupRules() {
  const res = await api.get('/marketing/group-rules')
  groupConfig.default_group = res.data.default_group || '未分组'
  groupConfig.rules = res.data.rules || []
}

async function loadOverallRules() {
  const res = await api.get('/marketing/overall-row-rules')
  overallConfig.rules = res.data.rules || []
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

async function saveGroupRules() {
  savingGroup.value = true
  try {
    await api.put('/marketing/group-rules', {
      default_group: groupConfig.default_group,
      rules: groupConfig.rules
    })
    ElMessage.success('组织分组规则已保存')
    await loadGroupRules()
    await loadPreviews()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingGroup.value = false
  }
}

async function saveOverallRules() {
  savingOverall.value = true
  try {
    await api.put('/marketing/overall-row-rules', { rules: overallConfig.rules })
    ElMessage.success('总体营销行分类规则已保存')
    await loadOverallRules()
    await loadPreviews()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingOverall.value = false
  }
}

onMounted(async () => {
  try {
    await Promise.all([loadGroupRules(), loadOverallRules()])
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
</style>
