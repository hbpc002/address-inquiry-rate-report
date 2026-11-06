<template>
  <div class="marketing-opening-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.marketing_opening_report }}</span>
          <el-button v-if="userStore.hasPermission('marketing_opening_report.export')" type="success" size="small" @click="handleExport">导出当前维度</el-button>
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
        <el-form-item v-if="searchForm.type === 'day'" label="录音日期">
          <el-date-picker v-model="searchForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'month'" label="录音月份">
          <el-date-picker v-model="searchForm.month" type="month" value-format="YYYY-MM" placeholder="选择月份" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="开始日期">
          <el-date-picker v-model="searchForm.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="结束日期">
          <el-date-picker v-model="searchForm.end_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="部门组">
          <el-select v-model="searchForm.department_group" placeholder="全部部门组" clearable filterable style="width: 160px">
            <el-option v-for="item in options.department_groups" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="searchForm.team" placeholder="全部班组" clearable filterable style="width: 170px">
            <el-option v-for="item in options.teams" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="searchForm.class_name" placeholder="全部班级" clearable filterable style="width: 150px">
            <el-option v-for="item in options.classes" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="五大产品已开口">
          <el-select v-model="searchForm.opened" placeholder="全部" clearable style="width: 100px">
            <el-option label="是" value="是" />
            <el-option label="否" value="否" />
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
        <div class="stat-item"><el-statistic title="接触量" :value="stats.contact_count" /></div>
        <div class="stat-item"><el-statistic title="五大产品已开口量" :value="stats.opened_count" /></div>
        <div class="stat-item"><el-statistic title="总开口率" :value="statsRate" :precision="2" suffix="%" /></div>
        <div class="stat-item"><el-statistic title="涉及员工" :value="stats.people_count" /></div>
      </el-row>

      <el-tabs v-model="dimension">
        <el-tab-pane label="员工" name="employee" />
        <el-tab-pane label="班组" name="team" />
        <el-tab-pane label="班级" name="class" />
        <el-tab-pane label="按日" name="day" />
      </el-tabs>

      <el-table :data="tableData" border stripe max-height="calc(100vh - 450px)">
        <template v-if="dimension === 'employee'">
          <el-table-column prop="kf_id" label="员工工号" width="120" sortable />
          <el-table-column prop="name" label="姓名" width="90" sortable />
          <el-table-column prop="team" label="班组" width="140" show-overflow-tooltip sortable />
          <el-table-column prop="dept" label="部门" width="150" show-overflow-tooltip sortable />
          <el-table-column prop="dept_group" label="部门组" width="120" show-overflow-tooltip sortable />
          <el-table-column prop="class_name" label="班级" width="120" show-overflow-tooltip sortable />
        </template>
        <template v-else-if="dimension === 'team'">
          <el-table-column prop="dept_group" label="部门组" width="120" sortable />
          <el-table-column prop="dept" label="部门" min-width="150" show-overflow-tooltip sortable />
          <el-table-column prop="team" label="班组" min-width="150" sortable />
          <el-table-column prop="people" label="人数" width="80" sortable />
        </template>
        <template v-else-if="dimension === 'class'">
          <el-table-column prop="dept_group" label="部门组" width="120" sortable />
          <el-table-column prop="dept" label="部门" min-width="150" show-overflow-tooltip sortable />
          <el-table-column prop="class_name" label="班级" min-width="140" sortable />
          <el-table-column prop="people" label="人数" width="80" sortable />
        </template>
        <template v-else>
          <el-table-column prop="date" label="录音日期" width="120" sortable />
          <el-table-column prop="people" label="人数" width="80" sortable />
        </template>
        <el-table-column prop="contact_count" label="接触量" width="90" sortable />
        <el-table-column prop="opened_count" label="已开口量" width="100" sortable />
        <el-table-column prop="opening_rate" label="总开口率" width="100" sortable>
          <template #default="{ row }">
            {{ formatRate(row.opening_rate) }}
          </template>
        </el-table-column>
        <el-table-column v-for="column in openingColumns" :key="column.key" :prop="column.key" :label="column.label" width="120" sortable />
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
  department_group: '',
  team: '',
  class_name: '',
  opened: '',
  name: '',
  emp_no: ''
})
const stats = reactive({ contact_count: 0, opened_count: 0, opening_rate: null, people_count: 0 })
const options = reactive({ teams: [], classes: [], department_groups: [] })
const result = ref({ employees: [], teams: [], classes: [], days: [], columns: [] })
const dimension = ref('employee')
const DEFAULT_OPENING_COLUMNS = [
  { key: 'active_overlay', label: '叠加包主动' },
  { key: 'opened_overlay', label: '叠加包已开' },
  { key: 'active_broadband', label: '宽带主动' },
  { key: 'opened_broadband', label: '宽带已开' },
  { key: 'active_mobile_new', label: '移网新装主动' },
  { key: 'opened_mobile_new', label: '移网新装已开' },
  { key: 'active_terminal', label: '终端主动' },
  { key: 'opened_terminal', label: '终端已开' },
  { key: 'active_package', label: '套餐主动' },
  { key: 'opened_package', label: '套餐已开' }
]
const openingColumns = computed(() => {
  const columns = result.value.columns || []
  return columns.length
    ? columns.map(column => ({
        ...column,
        label: column.action === '主动' ? `${column.product}主动` : `${column.product}已开`
      }))
    : DEFAULT_OPENING_COLUMNS
})
const dimensionKey = computed(() => ({ employee: 'employees', team: 'teams', class: 'classes', day: 'days' }[dimension.value]))
const tableData = computed(() => result.value[dimensionKey.value] || [])
const statsRate = computed(() => stats.opening_rate == null ? 0 : Number((stats.opening_rate * 100).toFixed(2)))

function formatRate(value) {
  if (value == null) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

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
  for (const key of ['department_group', 'team', 'class_name', 'name', 'emp_no']) {
    if (searchForm[key]) params[key] = searchForm[key]
  }
  if (searchForm.opened) params.five_products_opened = searchForm.opened
  return params
}

async function loadData() {
  try {
    const res = await api.get('/marketing-openings/report', { params: buildParams() })
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
    department_group: '',
    team: '',
    class_name: '',
    opened: '',
    name: '',
    emp_no: ''
  })
  dimension.value = 'employee'
  loadData()
}

function handleExport() {
  downloadBlob('/marketing-openings/report/export', {
    ...buildParams(),
    dimension: dimension.value
  }, '开口率报表.csv')
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
