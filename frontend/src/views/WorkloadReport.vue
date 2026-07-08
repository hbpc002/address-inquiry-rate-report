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
          <el-button @click="columnSelectorVisible = true">自定义列</el-button>
        </el-form-item>
      </el-form>

      <el-row :gutter="20" class="stats-row">
        <el-col :span="3">
          <el-statistic title="总人数" :value="stats.total_people" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="记录条数" :value="stats.total_records" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="呼入通话量" :value="stats.total_call_count" :precision="0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="平均通话均长" :value="averageCallDuration" :precision="1" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="工单总量" :value="stats.total_ticket_count" :precision="0" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="呼出量" :value="stats.total_outbound" :precision="0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="提单率(%)" :value="totalTiDanLv" :precision="2" />
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
                <el-table :data="teamRanking" size="small" border stripe max-height="280" @row-click="handleTeamRowClick">
                  <el-table-column label="班组" prop="team" />
                  <el-table-column label="人数" width="55" prop="count" />
                  <el-table-column label="总通话量" width="85" sortable prop="total_calls" />
                  <el-table-column label="平均通话均长" width="100" sortable prop="avg_duration" />
                  <el-table-column label="平均满意率" width="90" sortable prop="avg_satisfaction">
                    <template #default="{ row }">
                      {{ formatRate(row.avg_satisfaction) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="占比" width="100" sortable prop="total_calls">
                    <template #default="{ row }">
                      <span>{{ (row.total_calls / totalCallSum * 100).toFixed(1) }}%</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="提单率" width="85" sortable prop="ti_dan_lv">
                    <template #default="{ row }">
                      {{ (row.ti_dan_lv * 100).toFixed(2) + '%' }}
                    </template>
                  </el-table-column>
                  <el-table-column label="生成总量" width="85" sortable prop="total_ticket_count" />
                  <el-table-column label="人工呼出呼叫量" width="105" sortable prop="total_outbound" />
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
        <el-table-column v-for="col in visibleMetricColumns" :key="col.field" :label="col.label" :width="col.width" sortable="custom" :prop="col.field">
          <template #default="{ row }">
            {{ formatMetric(row, col.field, col.isRate) }}
          </template>
        </el-table-column>
        <el-table-column label="提单率" width="85" sortable="custom" prop="_ti_dan_lv">
          <template #default="{ row }">
            {{ (row._ti_dan_lv * 100).toFixed(2) + '%' }}
          </template>
        </el-table-column>
        <el-table-column label="接话绩效" width="100" sortable="custom" prop="_call_salary">
          <template #default="{ row }">
            {{ row._call_salary.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="满意度绩效" width="100" sortable="custom" prop="_sat_salary">
          <template #default="{ row }">
            {{ row._sat_salary !== null ? row._sat_salary.toFixed(2) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="合计绩效" width="100" sortable="custom" prop="_total_salary">
          <template #default="{ row }">
            {{ row._total_salary.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column v-for="target in salaryCfg.gapTargets" :key="target" :label="`话务量差额(${target})`" width="110" sortable="custom" :prop="`gap_${target}`">
          <template #default="{ row }">
            {{ row[`gap_${target}`] }}
          </template>
        </el-table-column>
        <el-table-column label="满意度差额" width="100" sortable="custom" prop="_sat_diff">
          <template #default="{ row }">
            {{ row._sat_diff !== null ? row._sat_diff.toFixed(2) : '-' }}
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

    <el-dialog v-model="columnSelectorVisible" title="自定义显示列" width="600px">
      <el-checkbox-group v-model="selectedColumns">
        <el-checkbox v-for="col in allMetricFields" :key="col.field" :label="col.field" style="margin: 4px 12px; width: 200px">
          <span :title="col.field">{{ col.label }}</span>
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="columnSelectorVisible = false">关闭</el-button>
      </template>
    </el-dialog>

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
            <el-table-column v-for="col in visibleDetailColumns" :key="col.field" :label="col.label" :width="col.width">
              <template #default="{ row }">
                {{ formatDetailValue(row, col) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
      <div v-else style="text-align: center; padding: 40px; color: #999">加载中...</div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'
import Echart from '../components/Echart.vue'
import { createPieOptions, CHART_COLORS } from '../utils/echarts'
import { getYesterday } from '../utils/date'
import { usePersistedFilters } from '../composables/usePersistedFilters'

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

const now = new Date()
const defaultMonth = now.toISOString().slice(0, 7)

const { filters: searchForm, isRestored: searchFormRestored } = usePersistedFilters(
  'workload-report-filters',
  {
    type: 'month',
    date: '',
    month: defaultMonth,
    start_date: '',
    end_date: '',
    name: '',
    account: '',
    team_desc: ''
  }
)

const stats = reactive({
  total_people: 0,
  total_records: 0,
  total_call_count: 0,
  total_work_duration: 0,
  total_ticket_count: 0,
  total_outbound: 0
})

const queryInfo = reactive({
  params: {},
  itemCount: 0,
  apiOk: false
})

const COLUMNS_KEY = 'workload-report-columns'
const DEFAULT_COLUMNS = [
  '呼入人工服务-人工服务-通话次数',
  '呼入人工服务-人工服务-通话总时长(秒)',
  '呼入人工服务-人工服务-通话均长(秒)',
  '呼入人工服务-人工服务-服务后整理总时长(秒)',
  '呼入人工服务-工单-生成总量',
  '人工服务-满意度-满意率',
  '呼入人工服务-解决率-解决率',
  '呼出服务-人工呼出呼叫量',
  '总体-工时利用率',
  '操作次数及时长-示忙次数',
  '呼入人工服务-满意度-非常满意量',
  '呼入人工服务-满意度-满意量',
  '呼入人工服务-满意度-一般量',
  '呼入人工服务-满意度-不满意量',
  '呼入人工服务-满意度-非常不满意量'
]
const DETAIL_COLUMNS = [
  '呼入人工服务-人工服务-通话次数',
  '呼入人工服务-人工服务-通话总时长(秒)',
  '呼入人工服务-人工服务-通话均长(秒)',
  '呼入人工服务-人工服务-服务后整理总时长(秒)',
  '呼入人工服务-工单-生成总量',
  '呼入人工服务-满意度-非常满意量',
  '呼出服务-人工呼出呼叫量',
  '操作次数及时长-示忙次数',
  '总体-工作总时长(秒)',
  '总体-工时利用率',
  '呼入人工服务-满意度-非常满意量',
  '呼入人工服务-满意度-满意量',
  '呼入人工服务-满意度-一般量',
  '呼入人工服务-满意度-不满意量',
  '呼入人工服务-满意度-非常不满意量'
]

function loadSelectedColumns() {
  try {
    const saved = localStorage.getItem(COLUMNS_KEY)
    return saved ? JSON.parse(saved) : [...DEFAULT_COLUMNS]
  } catch { return [...DEFAULT_COLUMNS] }
}

const allMetricFields = ref([])
const columnSelectorVisible = ref(false)
const selectedColumns = ref(loadSelectedColumns())

watch(selectedColumns, (val) => {
  localStorage.setItem(COLUMNS_KEY, JSON.stringify(val))
}, { deep: true })

function displayLabel(field) {
  return field.split('-').pop()
}

function isRateField(field) {
  return field.includes('率')
}

function getMetricValue(row, field) {
  const val = row.aggregated_metrics?.[field]
  if (val === null || val === undefined) return null
  return typeof val === 'number' ? val : parseFloat(val) || 0
}

function formatMetric(row, field, isRate = false) {
  const val = getMetricValue(row, field)
  if (val === null) return '-'
  if (isRate) return (val * 100).toFixed(2) + '%'
  if (Number.isInteger(val)) return String(val)
  return val.toFixed(1)
}

function formatRate(val) {
  if (val === null || val === undefined) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  if (isNaN(num)) return '-'
  return (num * 100).toFixed(2) + '%'
}

function formatDetailValue(row, col) {
  const val = row.metrics?.[col.field]
  if (val === null || val === undefined) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  if (isNaN(num)) return val
  if (col.isRate) return (num * 100).toFixed(2) + '%'
  if (Number.isInteger(num)) return String(num)
  return num.toFixed(1)
}

const visibleMetricColumns = computed(() => {
  return allMetricFields.value.filter(f => selectedColumns.value.includes(f.field))
})

const visibleDetailColumns = computed(() => {
  return allMetricFields.value
    .filter(f => DETAIL_COLUMNS.includes(f.field))
    .map(f => ({
      ...f,
      width: f.width + 5
    }))
})


const teamRanking = computed(() => {
  const teamMap = {}
  tableData.value.forEach(d => {
    const team = d.team_desc || '未知班组'
    if (!teamMap[team]) {
      teamMap[team] = { count: 0, total_calls: 0, total_duration: 0, total_satisfaction: 0, sat_count: 0, total_ticket_count: 0, total_outbound: 0 }
    }
    teamMap[team].count++
    teamMap[team].total_calls += getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    teamMap[team].total_ticket_count += getMetricValue(d, '呼入人工服务-工单-生成总量') || 0
    teamMap[team].total_outbound += getMetricValue(d, '呼出服务-人工呼出呼叫量') || 0
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
      total_ticket_count: data.total_ticket_count,
      total_outbound: data.total_outbound,
      ti_dan_lv: data.total_calls > 0 ? data.total_ticket_count / data.total_calls : 0,
      avg_duration: data.count > 0 ? (data.total_duration / data.count).toFixed(1) : 0,
      avg_satisfaction: data.sat_count > 0 ? (data.total_satisfaction / data.sat_count) : null
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
  return teamRanking.value.reduce((s, d) => s + d.total_calls, 0)
})

const averageCallDuration = computed(() => {
  const vals = tableData.value
    .map(d => getMetricValue(d, '呼入人工服务-人工服务-通话均长(秒)'))
    .filter(v => v !== null && v !== undefined)
  if (vals.length === 0) return 0
  const sum = vals.reduce((a, b) => a + b, 0)
  return Math.round(sum / vals.length * 10) / 10
})

const totalTiDanLv = computed(() => {
  if (!stats.total_call_count) return 0
  return +(stats.total_ticket_count / stats.total_call_count * 100).toFixed(2)
})

const salaryCfg = reactive({
  callTiers: [
    { min: 0, max: 1000, rate: 1.0 },
    { min: 1000, max: 2000, rate: 1.5 },
    { min: 2000, max: 3500, rate: 1.2 },
    { min: 3500, max: null, rate: 1.0 }
  ],
  satCoefficient: 0.5,
  satDiffA: 19,
  satDiffB: 20,
  gapTargets: [2000, 2500, 3000]
})

async function loadSalaryConfig() {
  try {
    const res = await api.get('/salary-config')
    const items = res.data.items || []
    for (const item of items) {
      if (item.rule_key === 'call_salary_tiers' && item.rule_data?.tiers) {
        salaryCfg.callTiers = item.rule_data.tiers
      } else if (item.rule_key === 'sat_salary') {
        salaryCfg.satCoefficient = item.rule_data.coefficient ?? 0.5
      } else if (item.rule_key === 'sat_diff') {
        salaryCfg.satDiffA = item.rule_data.coeff_a ?? 19
        salaryCfg.satDiffB = item.rule_data.coeff_b ?? 20
      } else if (item.rule_key === 'call_gap_targets') {
        salaryCfg.gapTargets = item.rule_data.targets || [2000, 2500, 3000]
      }
    }
  } catch { /* use defaults */ }
}

function calcCallSalary(callCount) {
  const tiers = salaryCfg.callTiers
  if (!tiers || tiers.length === 0) return 0
  let remaining = callCount
  let total = 0
  for (const tier of tiers) {
    if (remaining <= 0) break
    const bracketSize = tier.max === null ? remaining : Math.min(remaining, tier.max - tier.min)
    total += bracketSize * tier.rate
    remaining -= bracketSize
  }
  return total
}

function calcSatSalary(row) {
  const sat = getMetricValue(row, '呼入人工服务-满意度-非常满意量')
  const weight = getMetricValue(row, '呼入人工服务-满意度-满意量')
  if (sat === null || weight === null) return null
  return (sat + weight) * salaryCfg.satCoefficient
}

function calcSatDiff(row) {
  const e = getMetricValue(row, '呼入人工服务-满意度-非常满意量')
  const f = getMetricValue(row, '呼入人工服务-满意度-满意量')
  const g = getMetricValue(row, '呼入人工服务-满意度-一般量')
  const h = getMetricValue(row, '呼入人工服务-满意度-不满意量')
  const i = getMetricValue(row, '呼入人工服务-满意度-非常不满意量')
  if (e === null || f === null) return null
  const sumAll = [e, f, g, h, i].filter(v => v !== null).reduce((a, b) => a + b, 0)
  const sumEF = (e || 0) + (f || 0)
  return sumAll * salaryCfg.satDiffA - sumEF * salaryCfg.satDiffB
}

const filteredData = computed(() => {
  let data = tableData.value
  if (filterType.value === 'name') {
    data = data.filter(d => d.name === filterValue.value)
  } else if (filterType.value === 'team') {
    data = data.filter(d => d.team_desc === filterValue.value)
  }
  return data
})

const enrichedData = computed(() => {
  return filteredData.value.map(row => {
    const callCount = getMetricValue(row, '呼入人工服务-人工服务-通话次数') || 0
    const ticketCount = getMetricValue(row, '呼入人工服务-工单-生成总量') || 0
    const callSalary = calcCallSalary(callCount)
    const satSalary = calcSatSalary(row)
    const totalSalary = satSalary !== null ? callSalary + satSalary : callSalary

    const gapValues = {}
    for (const target of salaryCfg.gapTargets) {
      gapValues[`gap_${target}`] = target - callCount
    }

    const satDiffVal = calcSatDiff(row)

    return {
      ...row,
      _call_count: callCount,
      _ticket_count: ticketCount,
      _ti_dan_lv: callCount > 0 ? ticketCount / callCount : 0,
      _call_salary: callSalary,
      _sat_salary: satSalary,
      _total_salary: totalSalary,
      _sat_diff: satDiffVal,
      ...gapValues
    }
  })
})

const paginatedData = computed(() => {
  let data = enrichedData.value
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
      } else if (sortBy.value.startsWith('gap_') || sortBy.value.startsWith('_')) {
        aVal = a[sortBy.value] ?? 0
        bVal = b[sortBy.value] ?? 0
      } else {
        aVal = getMetricValue(a, sortBy.value) || 0
        bVal = getMetricValue(b, sortBy.value) || 0
      }
      return sortOrder.value === 'ascending' ? aVal - bVal : bVal - aVal
    })
  }
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return data.slice(start, end)
})

const teamChartOptions = computed(() => {
  if (!teamChartData.value.length) return {}
  return createPieOptions(teamChartData.value, '班组产量占比')
})


function handleSortChange({ prop, order }) {
  sortBy.value = prop || ''
  sortOrder.value = order || ''
  currentPage.value = 1
}

function handleTypeChange() {
  const d = new Date()
  if (searchForm.type === 'day') {
    searchForm.date = getYesterday()
    searchForm.month = ''
    searchForm.start_date = ''
    searchForm.end_date = ''
  } else if (searchForm.type === 'month') {
    searchForm.date = ''
    searchForm.month = d.toISOString().slice(0, 7)
    searchForm.start_date = ''
    searchForm.end_date = ''
  } else {
    searchForm.date = ''
    searchForm.month = ''
    searchForm.start_date = new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
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

const FALLBACK_FIELDS = [
  '呼入人工服务-人工服务-通话次数', '呼入人工服务-人工服务-通话总时长(秒)',
  '呼入人工服务-人工服务-通话均长(秒)', '呼入人工服务-人工服务-服务后整理总时长(秒)',
  '呼入人工服务-工单-生成总量', '人工服务-满意度-满意率',
  '呼入人工服务-解决率-解决率', '呼出服务-人工呼出呼叫量',
  '总体-工时利用率', '操作次数及时长-示忙次数',
  '呼入人工服务-满意度-非常满意量', '呼入人工服务-满意度-满意量',
  '呼入人工服务-满意度-一般量', '呼入人工服务-满意度-不满意量',
  '呼入人工服务-满意度-非常不满意量',
]

async function loadMetricsFields() {
  try {
    const res = await api.get('/workloads/metrics-fields')
    const fields = res.data
    if (!Array.isArray(fields) || fields.length === 0) {
      allMetricFields.value = FALLBACK_FIELDS.map(f => ({
        field: f, label: displayLabel(f), isRate: isRateField(f), width: 80
      }))
      return
    }
    allMetricFields.value = fields.map(f => ({
      field: f,
      label: displayLabel(f),
      isRate: isRateField(f),
      width: 80
    }))
  } catch {
    allMetricFields.value = FALLBACK_FIELDS.map(f => ({
      field: f, label: displayLabel(f), isRate: isRateField(f), width: 80
    }))
  }
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
    const data = res.data.items || []
    queryInfo.params = { ...params }
    queryInfo.itemCount = data.length
    queryInfo.apiOk = true
    console.log('[WorkloadReport] API response:', res.data)
    stats.total_people = res.data.stats.total_people
    stats.total_records = res.data.stats.total_records
    stats.total_call_count = res.data.stats.total_call_count
    stats.total_work_duration = res.data.stats.total_work_duration
    stats.total_ticket_count = res.data.stats.total_ticket_count
    stats.total_outbound = res.data.stats.total_outbound
    tableData.value = data

    if (res.data.stats.teams) {
      teams.value = res.data.stats.teams
    }

    if (data.length === 0) {
      const range = params.start_date
        ? params.start_date + (params.end_date !== params.start_date ? ' ~ ' + params.end_date : '')
        : (params.year_month || '当前')
      ElMessage.info(`所选日期(${range})没有工作量数据，请调整查询条件`)
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

onMounted(async () => {
  await loadSalaryConfig()
  if (!searchFormRestored) {
    handleTypeChange()
  }
  loadData()
  loadMetricsFields()
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
