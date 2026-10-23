<template>
  <div class="marketing-overall">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.marketing_overall_report }}</span>
          <el-button v-if="userStore.hasPermission('marketing_overall.export')" type="success" size="small" @click="handleExport">导出Excel</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="查询方式">
          <el-radio-group v-model="searchForm.type">
            <el-radio value="month">按月</el-radio>
            <el-radio value="range">自定义</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'month'" label="竣工月份">
          <el-date-picker v-model="searchForm.month" type="month" value-format="YYYY-MM" placeholder="选择月份" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="开始日期">
          <el-date-picker v-model="searchForm.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="结束日期">
          <el-date-picker v-model="searchForm.end_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="产品统计来源">
          <el-radio-group v-model="productSource" @change="loadData">
            <el-radio-button value="xszb">线上直办</el-radio-button>
            <el-radio-button value="fwgd">办理工单</el-radio-button>
            <el-radio-button value="all">合计</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="stats.unclassified_rows || stats.unclassified_business_rows"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
        :title="`有 ${stats.unclassified_rows} 条产品行未匹配行分类规则，${stats.unclassified_business_rows} 条产品行不属于当前统计业务类型；未分类数据不计入下表，请在营销设置中补充规则。`"
      />

      <div class="table-wrap">
        <table class="overall-table">
          <thead>
            <tr>
              <th class="col-no">序号</th>
              <th class="col-name">五大类业务</th>
              <th v-for="col in columns" :key="col.key" class="col-value metric-head">{{ col.label }}</th>
              <th class="col-value">合计</th>
              <th class="col-value">占比</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, index) in rows"
              :key="`${row.section_no}-${row.label}-${index}`"
              :class="[`bg-${row.bg}`, { 'subtotal-row': row.is_subtotal }]"
            >
              <td v-if="row.rowspan > 0" :rowspan="row.rowspan" class="col-no section-no">{{ row.section_no }}</td>
              <td class="col-name">{{ row.label }}</td>
              <td v-for="col in columns" :key="col.key" class="col-value">{{ row.counts[col.key] }}</td>
              <td class="col-value strong">{{ row.total }}</td>
              <td class="col-value" :class="{ 'ratio-empty': row.ratio === null }">{{ formatRatio(row.ratio) }}</td>
            </tr>
            <tr class="total-row">
              <td colspan="2" class="col-name">合计</td>
              <td v-for="col in columns" :key="col.key" class="col-value">{{ totalRow.counts[col.key] }}</td>
              <td class="col-value strong">{{ totalRow.total }}</td>
              <td class="col-value" :class="{ 'ratio-empty': !totalRow.total }">{{ totalRow.total ? '100.00%' : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="key-product-section">
        <div class="section-header">
          <span class="section-title">重点业务产品统计</span>
          <el-tag size="small">{{ keyProductSourceLabel }}</el-tag>
        </div>
        <el-alert
          v-if="!keyProductColumns.length"
          type="info"
          :closable="false"
          show-icon
          title="尚未配置重点业务产品，请先在营销设置中添加。"
        />
        <div v-else class="table-wrap">
          <table class="overall-table key-product-table">
            <thead>
              <tr>
                <th class="work-group-col">工作组</th>
                <th class="team-col">班组</th>
                <th v-for="col in keyProductColumns" :key="col.key" class="col-value metric-head">{{ col.label }}</th>
                <th class="col-value">合计</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in keyProductRows" :key="`${row.work_group}-${row.team}-${index}`">
                <td v-if="row.rowspan > 0" :rowspan="row.rowspan" class="work-group-col section-no">{{ row.work_group }}</td>
                <td class="team-col">{{ row.team }}</td>
                <td v-for="col in keyProductColumns" :key="col.key" class="col-value">{{ row.counts[col.key] }}</td>
                <td class="col-value strong">{{ row.total }}</td>
              </tr>
              <tr class="total-row">
                <td colspan="2" class="team-col">合计</td>
                <td v-for="col in keyProductColumns" :key="col.key" class="col-value">{{ keyProductTotalRow.counts[col.key] }}</td>
                <td class="col-value strong">{{ keyProductTotalRow.total }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api, useUserStore } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage } from 'element-plus'
import { downloadBlob } from '../utils/download'

const userStore = useUserStore()
const ui = useUiConfigStore()
const now = new Date()
const defaultMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
const searchForm = reactive({ type: 'month', month: defaultMonth, start_date: '', end_date: '' })
const stats = reactive({ grand_total: 0, unclassified_rows: 0, unclassified_business_rows: 0 })
const columns = ref([
  { key: 'overlay', label: '叠加包' },
  { key: 'package_change', label: '套餐变更' },
  { key: 'broadband_new', label: '宽带新装' },
  { key: 'mobile', label: '移网' },
  { key: 'terminal', label: '终端' }
])
const rows = ref([])
const totalRow = ref({ counts: {}, total: 0 })
const productSource = ref('xszb')
const keyProductColumns = ref([])
const keyProductRows = ref([])
const keyProductTotalRow = ref({ counts: {}, total: 0 })
const keyProductSourceLabel = ref('线上直办')

function buildParams() {
  const params = { product_source: productSource.value }
  if (searchForm.type === 'month' && searchForm.month) {
    params.year_month = searchForm.month
  } else if (searchForm.start_date && searchForm.end_date) {
    params.start_date = searchForm.start_date
    params.end_date = searchForm.end_date
  }
  return params
}

async function loadData() {
  try {
    const res = await api.get('/marketing/overall-report', { params: buildParams() })
    Object.assign(stats, res.data.stats)
    columns.value = res.data.columns
    rows.value = res.data.rows
    totalRow.value = res.data.total_row
    keyProductColumns.value = res.data.key_product_columns || []
    keyProductRows.value = res.data.key_product_rows || []
    keyProductTotalRow.value = res.data.key_product_total_row || { counts: {}, total: 0 }
    keyProductSourceLabel.value = res.data.key_product_source_label || ''
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

function formatRatio(value) {
  if (value === null || value === undefined) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function handleExport() {
  downloadBlob('/marketing/overall-report/export', buildParams(), '总体营销.xlsx')
}

onMounted(loadData)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.table-wrap {
  overflow-x: auto;
}
.overall-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  color: #303133;
  font-size: 14px;
}
.overall-table th,
.overall-table td {
  border: 1px solid #000;
  text-align: center;
  vertical-align: middle;
  padding: 8px 6px;
  height: 36px;
}
.overall-table th {
  font-weight: 700;
  background: #fff;
}
.overall-table .metric-head {
  color: #f00000;
}
.col-no { width: 60px; }
.col-name { width: 190px; }
.col-value { width: 105px; }
.strong { font-weight: 700; }
.section-no { font-weight: 700; }
.bg-blue { background: #ddebf7; }
.bg-pink { background: #fce4ec; }
.bg-green { background: #e2efda; }
.bg-yellow { background: #ffff00; }
.subtotal-row td { font-weight: 700; }
.total-row td { font-weight: 700; background: #fff; }
.ratio-empty {
  color: #00b050;
  background: #c6efce !important;
  font-weight: 700;
}
.key-product-section {
  margin-top: 24px;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #303133;
}
.key-product-table .work-group-col {
  width: 110px;
}
.key-product-table .team-col {
  width: 160px;
}
</style>
