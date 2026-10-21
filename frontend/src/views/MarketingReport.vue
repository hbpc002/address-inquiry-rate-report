<template>
  <div class="marketing-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.marketing_report }}</span>
          <el-button v-if="userStore.hasPermission('marketing_report.export')" type="success" size="small" @click="handleExport">导出当前维度</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="查询方式">
          <el-radio-group v-model="searchForm.type">
            <el-radio value="day">按天</el-radio>
            <el-radio value="month">按月</el-radio>
            <el-radio value="range">自定义</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'day'" label="竣工日期">
          <el-date-picker v-model="searchForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
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
        <el-form-item label="数据来源">
          <el-select v-model="searchForm.data_type" placeholder="全部来源" clearable style="width: 120px">
            <el-option v-for="item in options.sources" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="行分类">
          <el-select v-model="searchForm.group_name" placeholder="全部行分类" clearable filterable style="width: 160px">
            <el-option v-for="g in options.groups" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="searchForm.team" placeholder="全部班组" clearable filterable style="width: 140px">
            <el-option v-for="t in options.teams" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="重点业务">
          <el-select v-model="searchForm.business_type" placeholder="全部业务" clearable style="width: 120px">
            <el-option label="叠加包" value="叠加包" />
            <el-option label="套餐变更" value="套餐变更" />
          </el-select>
        </el-form-item>
        <el-form-item label="来话/去话">
          <el-select v-model="searchForm.lh_qh" placeholder="全部" clearable style="width: 100px">
            <el-option label="来话" value="来话" />
            <el-option label="去话" value="去话" />
          </el-select>
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="姓名" clearable style="width: 110px" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="searchForm.emp_no" placeholder="工号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-row class="stats-row">
        <div class="stat-item"><el-statistic title="产品办理量" :value="stats.total" /></div>
        <div class="stat-item"><el-statistic title="订单数" :value="stats.order_count" /></div>
        <div class="stat-item"><el-statistic title="来话办理量" :value="stats.inbound" /></div>
        <div class="stat-item"><el-statistic title="去话办理量" :value="stats.outbound" /></div>
        <div class="stat-item"><el-statistic title="叠加包" :value="stats.overlay" /></div>
        <div class="stat-item"><el-statistic title="套餐变更" :value="stats.package_change" /></div>
        <div class="stat-item"><el-statistic title="涉及员工" :value="stats.people_count" /></div>
      </el-row>

      <el-tabs v-model="dimension" @tab-change="loadData">
        <el-tab-pane label="员工" name="employee" />
        <el-tab-pane label="班组" name="team" />
        <el-tab-pane label="行分类" name="group" />
        <el-tab-pane label="产品" name="product" />
        <el-tab-pane label="按日趋势" name="day" />
      </el-tabs>

      <el-table :data="tableData" border stripe max-height="calc(100vh - 520px)">
        <template v-if="dimension === 'employee'">
          <el-table-column prop="kf_id" label="客服工号" width="120" />
          <el-table-column prop="name" label="姓名" width="90" />
          <el-table-column prop="team" label="班组" width="110" show-overflow-tooltip />
          <el-table-column prop="dept" label="部门" width="140" show-overflow-tooltip />
          <el-table-column prop="group_name" label="行分类" width="120" show-overflow-tooltip />
        </template>
        <template v-else-if="dimension === 'team'">
          <el-table-column prop="team" label="班组" width="140" show-overflow-tooltip />
          <el-table-column prop="people" label="人数" width="80" />
        </template>
        <template v-else-if="dimension === 'group'">
          <el-table-column prop="group_name" label="行分类" width="130" show-overflow-tooltip />
          <el-table-column prop="people" label="人数" width="80" />
        </template>
        <template v-else-if="dimension === 'product'">
          <el-table-column prop="product_id" label="产品ID" width="120" />
          <el-table-column prop="product_name" label="产品名称" min-width="240" show-overflow-tooltip />
        </template>
        <template v-else>
          <el-table-column prop="date" label="竣工日期" width="120" />
        </template>
        <el-table-column prop="total" label="产品办理量" width="110" sortable />
        <el-table-column prop="order_count" label="订单数" width="90" />
        <el-table-column prop="inbound" label="来话办理量" width="110" />
        <el-table-column prop="outbound" label="去话办理量" width="110" />
        <el-table-column prop="overlay" label="叠加包" width="90" />
        <el-table-column prop="overlay_day" label="日包" width="80" />
        <el-table-column prop="overlay_month" label="月包" width="80" />
        <el-table-column prop="overlay_long" label="长期包" width="90" />
        <el-table-column prop="overlay_undefined" label="未定义" width="90" />
        <el-table-column prop="package_change" label="套餐变更" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api, useUserStore } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage } from 'element-plus'
import { downloadBlob } from '../utils/download'

const userStore = useUserStore()
const ui = useUiConfigStore()
const now = new Date()
const defaultMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
const searchForm = reactive({
  type: 'month',
  date: '',
  month: defaultMonth,
  start_date: '',
  end_date: '',
  group_name: '',
  data_type: '',
  team: '',
  business_type: '',
  lh_qh: '',
  name: '',
  emp_no: ''
})
const stats = reactive({
  total: 0,
  order_count: 0,
  inbound: 0,
  outbound: 0,
  overlay: 0,
  package_change: 0,
  people_count: 0
})
const options = reactive({ groups: [], teams: [], orgs: [], products: [], sources: [] })
const result = ref({ employees: [], teams: [], groups: [], products: [], days: [] })
const dimension = ref('employee')
const dimensionKey = computed(() => ({ employee: 'employees', team: 'teams', group: 'groups', product: 'products', day: 'days' }[dimension.value]))
const tableData = computed(() => result.value[dimensionKey.value] || [])

function buildParams() {
  const params = {}
  if (searchForm.type === 'day' && searchForm.date) {
    params.start_date = searchForm.date
    params.end_date = searchForm.date
  } else if (searchForm.type === 'month' && searchForm.month) {
    params.year_month = searchForm.month
  } else if (searchForm.type === 'range' && searchForm.start_date && searchForm.end_date) {
    params.start_date = searchForm.start_date
    params.end_date = searchForm.end_date
  }
  for (const key of ['group_name', 'data_type', 'team', 'business_type', 'lh_qh', 'name', 'emp_no']) {
    if (searchForm[key]) params[key] = searchForm[key]
  }
  return params
}

async function loadData() {
  try {
    const res = await api.get('/marketing/report', { params: buildParams() })
    Object.assign(stats, res.data.stats)
    result.value = res.data
    Object.assign(options, res.data.options || {})
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

function resetFilters() {
  Object.assign(searchForm, {
    type: 'month',
    date: '',
    month: defaultMonth,
    start_date: '',
    end_date: '',
    group_name: '',
    data_type: '',
    team: '',
    business_type: '',
    lh_qh: '',
    name: '',
    emp_no: ''
  })
  loadData()
}

function handleExport() {
  downloadBlob('/marketing/report/export', { ...buildParams(), dimension: dimension.value }, 'marketing_report.csv')
}

onMounted(loadData)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stats-row {
  display: flex;
  flex-wrap: nowrap;
  gap: 20px;
  margin-bottom: 16px;
}
.stat-item {
  flex: 1 1 0;
  min-width: 0;
}
</style>
