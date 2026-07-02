<template>
  <div class="workload-report">
    <el-card>
      <template #header>
        <span>工作量报表</span>
      </template>

      <el-form inline>
        <el-form-item label="查询方式">
          <el-radio-group v-model="searchForm.type" @change="handleTypeChange">
            <el-radio value="day">按天</el-radio>
            <el-radio value="month">按月</el-radio>
            <el-radio value="range">自定义</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <el-form inline>
        <el-form-item v-if="searchForm.type === 'day'" label="日期">
          <el-date-picker v-model="searchForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'month'" label="月份">
          <el-date-picker v-model="searchForm.month" type="month" value-format="YYYY-MM" placeholder="选择月份" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="开始日期">
          <el-date-picker v-model="searchForm.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="结束日期">
          <el-date-picker v-model="searchForm.end_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="请输入姓名" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="账号">
          <el-input v-model="searchForm.account" placeholder="请输入账号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="searchForm.team_desc" placeholder="全部班组" clearable filterable style="width: 140px">
            <el-option v-for="t in teams" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-row :gutter="20" class="stats-row">
        <el-col :span="4">
          <el-statistic title="总人数" :value="stats.total_people" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="记录条数" :value="stats.total_records" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="呼入通话量" :value="stats.total_call_count" :precision="0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="总工时(秒)" :value="stats.total_work_duration" :precision="0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="工单总量" :value="stats.total_ticket_count" :precision="0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="呼出量" :value="stats.total_outbound" :precision="0" />
        </el-col>
      </el-row>

      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 20px">
        <el-col :span="14">
          <el-card shadow="hover">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span>个人排名</span>
                <el-tag v-if="filterType === 'name'" closable @close="clearFilter" type="warning">
                  已筛选: {{ filterValue }}
                </el-tag>
              </div>
            </template>
            <el-table :data="personalRanking" size="small" max-height="320" border stripe @row-click="handlePersonRowClick">
              <el-table-column label="#" width="45" type="index" />
              <el-table-column label="姓名" width="80" prop="name" />
              <el-table-column label="通话次数" width="85" sortable :sort-method="sortMetric('呼入人工服务-人工服务-通话次数')" prop="call_count" />
              <el-table-column label="通话均长" width="85" sortable :sort-method="sortMetric('呼入人工服务-人工服务-通话均长(秒)')" prop="avg_duration" />
              <el-table-column label="满意率" width="75" sortable :sort-method="sortMetric('人工服务-满意度-满意率')" prop="satisfaction" />
              <el-table-column label="解决率" width="75" sortable :sort-method="sortMetric('呼入人工服务-解决率-解决率')" prop="resolve_rate" />
              <el-table-column label="工单量" width="70" sortable :sort-method="sortMetric('呼入人工服务-工单-生成总量')" prop="ticket_count" />
              <el-table-column label="呼出量" width="70" sortable :sort-method="sortMetric('呼出服务-人工呼出呼叫量')" prop="outbound" />
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card shadow="hover">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span>班组排名</span>
                <el-tag v-if="filterType === 'team'" closable @close="clearFilter" type="warning">
                  已筛选: {{ filterValue }}
                </el-tag>
              </div>
            </template>
            <el-table :data="teamRanking" size="small" max-height="320" border stripe @row-click="handleTeamRowClick">
              <el-table-column label="#" width="45" type="index" />
              <el-table-column label="班组" width="100" prop="team" />
              <el-table-column label="人数" width="55" prop="count" />
              <el-table-column label="总通话量" width="85" sortable prop="total_calls" />
              <el-table-column label="平均通话均长" width="100" sortable prop="avg_duration" />
              <el-table-column label="平均满意率" width="90" sortable prop="avg_satisfaction" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 20px">
        <el-col :span="24">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; font-size: 14px; color: #606266">班组产量占比</div>
            <el-row>
              <el-col :span="8">
                <Echart :options="teamChartOptions" height="280px" />
              </el-col>
              <el-col :span="16">
                <el-table :data="teamChartData" size="small" border stripe max-height="280">
                  <el-table-column label="班组" prop="name" />
                  <el-table-column label="通话量" prop="value" sortable />
                  <el-table-column label="占比" width="100">
                    <template #default="{ row }">
                      <span>{{ (row.value / totalCallSum * 100).toFixed(1) }}%</span>
                    </template>
                  </el-table-column>
                </el-table>
              </el-col>
            </el-row>
          </el-card>
        </el-col>
      </el-row>

      <el-table
        ref="detailTable"
        :data="paginatedData"
        border stripe
        max-height="calc(100vh - 350px)"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="account" label="账号" width="110" />
        <el-table-column prop="name" label="姓名" width="80" sortable="custom" />
        <el-table-column prop="emp_no" label="工号" width="80" />
        <el-table-column prop="team_desc" label="班组" min-width="140" sortable="custom" />
        <el-table-column prop="date_count" label="天数" width="60" sortable="custom" />
        <el-table-column label="通话次数" width="80" sortable="custom" prop="call_count">
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-人工服务-通话次数') }}
          </template>
        </el-table-column>
        <el-table-column label="通话总时长" width="90" sortable="custom" prop="call_duration">
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-人工服务-通话总时长(秒)') }}
          </template>
        </el-table-column>
        <el-table-column label="通话均长" width="80" sortable="custom" prop="avg_duration">
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-人工服务-通话均长(秒)') }}
          </template>
        </el-table-column>
        <el-table-column label="整理总时长" width="90" sortable="custom" prop="organize_duration">
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-人工服务-服务后整理总时长(秒)') }}
          </template>
        </el-table-column>
        <el-table-column label="工单总量" width="70" sortable="custom" prop="ticket_count">
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-工单-生成总量') }}
          </template>
        </el-table-column>
        <el-table-column label="满意率" width="70" sortable="custom" prop="satisfaction">
          <template #default="{ row }">
            {{ formatMetric(row, '人工服务-满意度-满意率', '%') }}
          </template>
        </el-table-column>
        <el-table-column label="解决率" width="70" sortable="custom" prop="resolve_rate">
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-解决率-解决率', '%') }}
          </template>
        </el-table-column>
        <el-table-column label="呼出呼叫量" width="80" sortable="custom" prop="outbound">
          <template #default="{ row }">
            {{ formatMetric(row, '呼出服务-人工呼出呼叫量') }}
          </template>
        </el-table-column>
        <el-table-column label="工时利用率" width="80" sortable="custom" prop="utilization">
          <template #default="{ row }">
            {{ formatMetric(row, '总体-工时利用率', '%') }}
          </template>
        </el-table-column>
        <el-table-column label="示忙次数" width="70" sortable="custom" prop="busy_count">
          <template #default="{ row }">
            {{ formatMetric(row, '操作次数及时长-示忙次数') }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="tableData.length > 0"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="filteredData.length"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 15px; justify-content: flex-end"
      />
    </el-card>

    <el-drawer v-model="drawerVisible" :title="drawerTitle" size="50%" direction="rtl">
      <template v-if="personalRecords.length">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="账号">{{ personalRecords[0].account }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ personalRecords[0].name }}</el-descriptions-item>
          <el-descriptions-item label="工号">{{ personalRecords[0].emp_no }}</el-descriptions-item>
          <el-descriptions-item label="班组">{{ personalRecords[0].team_desc }}</el-descriptions-item>
        </el-descriptions>

        <div style="overflow-x: auto;">
          <el-table :data="personalRecords" border stripe size="small" max-height="500">
            <el-table-column prop="date" label="日期" width="90" />
            <el-table-column label="通话次数" width="70">
              <template #default="{ row }">{{ getMetric(row, '呼入人工服务-人工服务-通话次数') }}</template>
            </el-table-column>
            <el-table-column label="通话总时长" width="80">
              <template #default="{ row }">{{ getMetric(row, '呼入人工服务-人工服务-通话总时长(秒)') }}s</template>
            </el-table-column>
            <el-table-column label="通话均长" width="70">
              <template #default="{ row }">{{ getMetric(row, '呼入人工服务-人工服务-通话均长(秒)') }}s</template>
            </el-table-column>
            <el-table-column label="整理时长" width="70">
              <template #default="{ row }">{{ getMetric(row, '呼入人工服务-人工服务-服务后整理总时长(秒)') }}s</template>
            </el-table-column>
            <el-table-column label="工单总量" width="65">
              <template #default="{ row }">{{ getMetric(row, '呼入人工服务-工单-生成总量') }}</template>
            </el-table-column>
            <el-table-column label="非常满意" width="65">
              <template #default="{ row }">{{ getMetric(row, '人工服务-满意度-非常满意量') }}</template>
            </el-table-column>
            <el-table-column label="呼出量" width="65">
              <template #default="{ row }">{{ getMetric(row, '呼出服务-人工呼出呼叫量') }}</template>
            </el-table-column>
            <el-table-column label="示忙次数" width="65">
              <template #default="{ row }">{{ getMetric(row, '操作次数及时长-示忙次数') }}</template>
            </el-table-column>
            <el-table-column label="总工时(秒)" width="75">
              <template #default="{ row }">{{ getMetric(row, '总体-工作总时长(秒)') }}</template>
            </el-table-column>
            <el-table-column label="工时利用率" width="70">
              <template #default="{ row }">{{ getMetric(row, '总体-工时利用率') }}%</template>
            </el-table-column>
          </el-table>
        </div>
      </template>
      <div v-else style="text-align: center; padding: 40px; color: #999">加载中...</div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'
import Echart from '../components/Echart.vue'
import { createPieOptions, CHART_COLORS } from '../utils/echarts'
import { getYesterday } from '../utils/date'

const tableData = ref([])
const teams = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const drawerVisible = ref(false)
const drawerTitle = ref('')
const personalRecords = ref([])
const filterType = ref('')
const filterValue = ref('')
const sortBy = ref('')
const sortOrder = ref('')

const searchForm = reactive({
  type: 'day',
  date: getYesterday(),
  month: new Date().toISOString().slice(0, 7),
  start_date: '',
  end_date: '',
  name: '',
  account: '',
  team_desc: ''
})

const stats = reactive({
  total_people: 0,
  total_records: 0,
  total_call_count: 0,
  total_work_duration: 0,
  total_ticket_count: 0,
  total_outbound: 0
})

function getMetricValue(row, field) {
  const val = row.aggregated_metrics?.[field]
  if (val === null || val === undefined) return null
  return typeof val === 'number' ? val : parseFloat(val) || 0
}

function formatMetric(row, field, suffix = '') {
  const val = getMetricValue(row, field)
  if (val === null) return '-'
  if (Number.isInteger(val)) return val + suffix
  return val.toFixed(1) + suffix
}

function getMetric(row, field) {
  const val = row.metrics?.[field]
  if (val === null || val === undefined) return '-'
  if (typeof val === 'number') {
    if (Number.isInteger(val)) return val
    return val.toFixed(1)
  }
  return val
}

const personalRanking = computed(() => {
  return [...tableData.value]
    .map(d => ({
      ...d,
      call_count: getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0,
      avg_duration: getMetricValue(d, '呼入人工服务-人工服务-通话均长(秒)'),
      satisfaction: getMetricValue(d, '人工服务-满意度-满意率'),
      resolve_rate: getMetricValue(d, '呼入人工服务-解决率-解决率'),
      ticket_count: getMetricValue(d, '呼入人工服务-工单-生成总量') || 0,
      outbound: getMetricValue(d, '呼出服务-人工呼出呼叫量') || 0
    }))
    .sort((a, b) => b.call_count - a.call_count)
})

const teamRanking = computed(() => {
  const teamMap = {}
  tableData.value.forEach(d => {
    const team = d.team_desc || '未知班组'
    if (!teamMap[team]) {
      teamMap[team] = { count: 0, total_calls: 0, total_duration: 0, total_satisfaction: 0, sat_count: 0 }
    }
    teamMap[team].count++
    teamMap[team].total_calls += getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    const avgDur = getMetricValue(d, '呼入人工服务-人工服务-通话均长(秒)')
    if (avgDur !== null) {
      teamMap[team].total_duration += avgDur
    }
    const sat = getMetricValue(d, '人工服务-满意度-满意率')
    if (sat !== null) {
      teamMap[team].total_satisfaction += sat
      teamMap[team].sat_count++
    }
  })
  return Object.entries(teamMap)
    .map(([team, data]) => ({
      team,
      count: data.count,
      total_calls: data.total_calls,
      avg_duration: data.count > 0 ? (data.total_duration / data.count).toFixed(1) : 0,
      avg_satisfaction: data.sat_count > 0 ? (data.total_satisfaction / data.sat_count).toFixed(2) : 0
    }))
    .sort((a, b) => b.total_calls - a.total_calls)
})

const teamChartData = computed(() => {
  const teamMap = {}
  tableData.value.forEach(d => {
    const team = d.team_desc || '未知班组'
    if (!teamMap[team]) teamMap[team] = 0
    teamMap[team] += getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
  })
  return Object.entries(teamMap)
    .map(([name, value]) => ({ name, value: Math.round(value) }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
})

const totalCallSum = computed(() => {
  return teamChartData.value.reduce((s, d) => s + d.value, 0)
})

const teamChartOptions = computed(() => {
  if (!teamChartData.value.length) return {}
  return createPieOptions(teamChartData.value, '班组产量占比')
})

const filteredData = computed(() => {
  let data = tableData.value
  if (filterType.value === 'name') {
    data = data.filter(d => d.name === filterValue.value)
  } else if (filterType.value === 'team') {
    data = data.filter(d => d.team_desc === filterValue.value)
  }
  return data
})

const paginatedData = computed(() => {
  let data = filteredData.value
  if (sortBy.value && sortOrder.value) {
    data = [...data].sort((a, b) => {
      let aVal, bVal
      if (sortBy.value === 'name' || sortBy.value === 'team_desc') {
        aVal = (a[sortBy.value] || '').toLowerCase()
        bVal = (b[sortBy.value] || '').toLowerCase()
        return sortOrder.value === 'ascending' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
      }
      if (sortBy.value === 'date_count') {
        aVal = a.date_count || 0
        bVal = b.date_count || 0
      } else {
        aVal = getMetricValue(a, METRIC_MAP[sortBy.value] || '') || 0
        bVal = getMetricValue(b, METRIC_MAP[sortBy.value] || '') || 0
      }
      return sortOrder.value === 'ascending' ? aVal - bVal : bVal - aVal
    })
  }
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return data.slice(start, end)
})

const METRIC_MAP = {
  call_count: '呼入人工服务-人工服务-通话次数',
  call_duration: '呼入人工服务-人工服务-通话总时长(秒)',
  avg_duration: '呼入人工服务-人工服务-通话均长(秒)',
  organize_duration: '呼入人工服务-人工服务-服务后整理总时长(秒)',
  ticket_count: '呼入人工服务-工单-生成总量',
  satisfaction: '人工服务-满意度-满意率',
  resolve_rate: '呼入人工服务-解决率-解决率',
  outbound: '呼出服务-人工呼出呼叫量',
  utilization: '总体-工时利用率',
  busy_count: '操作次数及时长-示忙次数'
}

function sortMetric(field) {
  return (a, b) => {
    const aVal = getMetricValue(a, field) || 0
    const bVal = getMetricValue(b, field) || 0
    return aVal - bVal
  }
}

function handleSortChange({ prop, order }) {
  sortBy.value = prop || ''
  sortOrder.value = order || ''
  currentPage.value = 1
}

function handleTypeChange() {
  const now = new Date()
  if (searchForm.type === 'day') {
    searchForm.date = getYesterday()
    searchForm.month = ''
    searchForm.start_date = ''
    searchForm.end_date = ''
  } else if (searchForm.type === 'month') {
    searchForm.date = ''
    searchForm.month = now.toISOString().slice(0, 7)
    searchForm.start_date = ''
    searchForm.end_date = ''
  } else {
    searchForm.date = ''
    searchForm.month = ''
    searchForm.start_date = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
    searchForm.end_date = getYesterday()
  }
}

function handlePersonRowClick(row) {
  if (filterType.value === 'name' && filterValue.value === row.name) {
    clearFilter()
  } else {
    filterType.value = 'name'
    filterValue.value = row.name
    currentPage.value = 1
  }
}

function handleTeamRowClick(row) {
  if (filterType.value === 'team' && filterValue.value === row.team) {
    clearFilter()
  } else {
    filterType.value = 'team'
    filterValue.value = row.team
    currentPage.value = 1
  }
}

function clearFilter() {
  filterType.value = ''
  filterValue.value = ''
  currentPage.value = 1
}

async function loadData() {
  try {
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
    if (searchForm.name) params.name = searchForm.name
    if (searchForm.account) params.account = searchForm.account
    if (searchForm.team_desc) params.team_desc = searchForm.team_desc

    const res = await api.get('/workloads/report', { params })
    stats.total_people = res.data.stats.total_people
    stats.total_records = res.data.stats.total_records
    stats.total_call_count = res.data.stats.total_call_count
    stats.total_work_duration = res.data.stats.total_work_duration
    stats.total_ticket_count = res.data.stats.total_ticket_count
    stats.total_outbound = res.data.stats.total_outbound
    tableData.value = res.data.items || []

    if (res.data.stats.teams) {
      teams.value = res.data.stats.teams
    }
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

function getDetailDateRange() {
  let startDate, endDate
  if (searchForm.type === 'day' && searchForm.date) {
    startDate = searchForm.date
    endDate = searchForm.date
  } else if (searchForm.type === 'month' && searchForm.month) {
    startDate = searchForm.month + '-01'
    const [y, m] = searchForm.month.split('-').map(Number)
    const lastDay = new Date(y, m, 0).getDate()
    endDate = `${searchForm.month}-${String(lastDay).padStart(2, '0')}`
  } else if (searchForm.type === 'range' && searchForm.start_date && searchForm.end_date) {
    startDate = searchForm.start_date
    endDate = searchForm.end_date
  } else {
    const now = new Date()
    endDate = getYesterday()
    startDate = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-01'
  }
  return { startDate, endDate }
}

async function openDetail(row) {
  drawerTitle.value = `${row.name}（${row.account}）工作量明细`
  personalRecords.value = []
  drawerVisible.value = true

  try {
    const { startDate, endDate } = getDetailDateRange()
    const params = { limit: 100 }
    if (startDate && endDate) {
      params.start_date = startDate
      params.end_date = endDate
    }
    params.account = row.account
    const res = await api.get('/workloads', { params })
    personalRecords.value = res.data.items || []
  } catch (e) {
    ElMessage.error('加载个人明细失败')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}
</style>