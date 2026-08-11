<template>
  <div class="workload-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>工作量报表</span>
          <span>
            <el-button v-if="userStore.hasPermission('workload_report.screenshot')" type="primary" size="small" :loading="screenshotLoading" @click="handleScreenshot">截图导出</el-button>
            <el-button v-if="userStore.hasPermission('workload_report.export')" type="success" size="small" @click="handleExport">导出</el-button>
            <el-button v-if="userStore.hasPermission('workload_report.export')" type="warning" size="small" @click="handleExportFiltered">导出筛选</el-button>
          </span>
        </div>
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
            <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="searchForm.class_name" placeholder="全部班级" clearable filterable style="width: 120px">
            <el-option v-for="c in classOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="入职时长">
          <el-select v-model="searchForm.tenure_mode" placeholder="全部" clearable style="width: 90px">
            <el-option label="全部" value="" />
            <el-option label="≤" value="le" />
            <el-option label=">" value="gt" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="searchForm.tenure_mode">
          <el-input-number v-model="searchForm.tenure_months" :min="1" :max="120" style="width: 100px" />
          <span style="margin-left: 4px">月</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="columnSelectorVisible = true">自定义列</el-button>
        </el-form-item>
      </el-form>

      <div style="margin-bottom: 12px">
        <FieldFilterPanel
          :fields="filterFields"
          v-model="fieldFilter.conditions"
          :loading="dataLoading"
          persist-key="workload-report-field-filter"
          @change="handleFieldFilterChange"
        />
      </div>

      <el-row :gutter="20" class="stats-row">
        <el-col :span="3">
          <el-statistic title="总人数" :value="stats.total_people" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="记录条数" :value="stats.total_records" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="呼入通话量" :value="stats.total_call_count" :precision="0" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="平均通话均长" :value="averageCallDuration" :precision="1" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="工单总量" :value="stats.total_ticket_count" :precision="0" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="呼出量" :value="stats.total_outbound" :precision="0" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="提单率(%)" :value="totalTiDanLv" :precision="2" :value-style="getMetricStyle('_ti_dan_lv', totalTiDanLv)" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="满意率(%)" :value="totalSatisfactionRate" :precision="2" />
        </el-col>
      </el-row>


      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 20px">
        <el-col :span="24">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; font-size: 14px; color: #606266; display: flex; align-items: center; gap: 12px;">
              <span>班组产量占比</span>
              <el-radio-group v-model="viewMode" size="small">
                <el-radio-button value="team">按班组</el-radio-button>
                <el-radio-button value="class">按班级</el-radio-button>
              </el-radio-group>
            </div>
            <el-row>
              <el-col :span="8">
                <Echart :options="teamChartOptions" height="280px" @click="handlePieClick" />
              </el-col>
              <el-col :span="16">
                <el-table v-if="viewMode === 'team'" :data="classFilter ? classFilteredRanking : teamRanking" size="small" border stripe max-height="280" @row-click="handleTeamRowClick">
                  <el-table-column label="排名" width="55" type="index" />
                  <el-table-column label="班组" prop="team" />
                  <el-table-column label="组长" prop="leader" min-width="60" />
                  <el-table-column label="人数" width="55" prop="count" />
                  <el-table-column label="总通话量" width="85" sortable prop="total_calls" />
                  <el-table-column label="平均通话均长" width="100" sortable prop="avg_duration" />
                  <el-table-column label="平均满意率" width="90" sortable prop="avg_satisfaction">
                    <template #default="{ row }">
                      <span :style="getMetricStyle('人工服务-满意度-满意率', row.avg_satisfaction)">{{ formatRate(row.avg_satisfaction) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="占比" width="100" sortable prop="total_calls">
                    <template #default="{ row }">
                      <span>{{ (row.total_calls / filteredCallSum * 100).toFixed(1) }}%</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="提单率" width="85" sortable prop="ti_dan_lv">
                    <template #default="{ row }">
                      <span :style="getMetricStyle('_ti_dan_lv', row.ti_dan_lv)">{{ (row.ti_dan_lv * 100).toFixed(2) + '%' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="人均通话量(含组长、师傅)" width="120" sortable prop="avg_calls_per_person_all" />
                  <el-table-column label="人均通话量(组员)" width="105" sortable prop="avg_calls_per_person_member" />
                  <el-table-column label="接话小时量" width="90" sortable prop="member_call_hourly_rate">
                    <template #default="{ row }">
                      {{ row.member_call_hourly_rate.toFixed(1) }}
                    </template>
                  </el-table-column>
                </el-table>
                <el-table v-else :data="classRanking" size="small" border stripe max-height="280">
                  <el-table-column label="排名" width="55" type="index" />
                  <el-table-column label="班级" prop="name" />
                  <el-table-column label="班组数" width="65" prop="team_count" />
                  <el-table-column label="人数" width="55" prop="count" />
                  <el-table-column label="总通话量" width="85" sortable prop="total_calls" />
                  <el-table-column label="平均通话均长" width="100" sortable prop="avg_duration" />
                  <el-table-column label="平均满意率" width="90" sortable prop="avg_satisfaction">
                    <template #default="{ row }">
                      <span :style="getMetricStyle('人工服务-满意度-满意率', row.avg_satisfaction)">{{ formatRate(row.avg_satisfaction) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="占比" width="100" sortable prop="total_calls">
                    <template #default="{ row }">
                      <span>{{ (row.total_calls / classCallSum * 100).toFixed(1) }}%</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="提单率" width="85" sortable prop="ti_dan_lv">
                    <template #default="{ row }">
                      <span>{{ (row.ti_dan_lv * 100).toFixed(2) + '%' }}</span>
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
        <ColumnWithTip v-for="col in visibleMetricColumns" :key="col.field" :label="col.label" :width="col.width" sortable="custom" :prop="col.field" :annotation="workloadAnnMap[col.field]">
          <template #default="{ row }">
            <span :style="getMetricStyle(col.field, getMetricValue(row, col.field))">{{ formatMetric(row, col.field, col.isRate) }}</span>
          </template>
        </ColumnWithTip>
        <ColumnWithTip label="提单率" width="85" sortable="custom" prop="_ti_dan_lv" :annotation="workloadAnnMap['_ti_dan_lv']">
          <template #default="{ row }">
            <span :style="getMetricStyle('_ti_dan_lv', row._ti_dan_lv)">{{ (row._ti_dan_lv * 100).toFixed(2) + '%' }}</span>
          </template>
        </ColumnWithTip>
        <ColumnWithTip label="接话小时量" width="90" sortable="custom" prop="_call_hourly_rate" :annotation="workloadAnnMap['_call_hourly_rate']">
          <template #default="{ row }">
            {{ row._call_hourly_rate.toFixed(1) }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="userStore.hasPermission('workload_report.view_call_salary')" label="接话绩效(预测)" width="100" sortable="custom" prop="_call_salary" :annotation="workloadAnnMap['_call_salary']">
          <template #default="{ row }">
            {{ row._call_salary.toFixed(2) }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="userStore.hasPermission('workload_report.view_sat_salary')" label="满意度绩效(预测)" width="100" sortable="custom" prop="_sat_salary" :annotation="workloadAnnMap['_sat_salary']">
          <template #default="{ row }">
            {{ row._sat_salary !== null ? row._sat_salary.toFixed(2) : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="userStore.hasPermission('workload_report.view_total_salary')" label="合计绩效(预测)" width="100" sortable="custom" prop="_total_salary" :annotation="workloadAnnMap['_total_salary']">
          <template #default="{ row }">
            {{ row._total_salary.toFixed(2) }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="userStore.hasPermission('workload_report.view_gap')" v-for="target in salaryCfg.gapTargets" :key="target" :label="`话务量差额(${target})`" width="110" sortable="custom" :prop="`gap_${target}`" :annotation="workloadAnnMap[`gap_${target}`]">
          <template #default="{ row }">
            {{ row[`gap_${target}`] }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="userStore.hasPermission('workload_report.view_sat_diff')" label="满意度差额" width="100" sortable="custom" prop="_sat_diff" :annotation="workloadAnnMap['_sat_diff']">
          <template #default="{ row }">
            {{ row._sat_diff !== null ? row._sat_diff.toFixed(2) : '-' }}
          </template>
        </ColumnWithTip>
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
        :total="fieldFilter.filtered(enrichedData).length"
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
import { createPieOptions, createBarOptions, CHART_COLORS } from '../utils/echarts'
import { getYesterday } from '../utils/date'
import { getWorkloadDetailDateRange } from '../utils/workloadDetailRange'
import { useUserStore } from '../stores/user'
const userStore = useUserStore()
import { downloadBlob } from '../utils/download'
import html2canvas from 'html2canvas'
import { usePersistedFilters } from '../composables/usePersistedFilters'
import ColumnWithTip from '../components/ColumnWithTip.vue'
import { useFieldAnnotations } from '../composables/useFieldAnnotations'
import FieldFilterPanel from '../components/FieldFilterPanel.vue'
import { useFieldFilter } from '../composables/useFieldFilter'

const tableData = ref([])
const workloadAnnotator = useFieldAnnotations('workload')
const workloadAnnMap = ref({})
const teams = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const screenshotLoading = ref(false)
const drawerVisible = ref(false)
const drawerTitle = ref('')
const personalRecords = ref([])
const filterType = ref('')
const filterValue = ref('')
const sortBy = ref('')
const sortOrder = ref('')
const viewMode = ref('team')
const classFilter = ref('')
const teamLeaders = ref({})
const classOptions = computed(() => {
  const classes = new Set()
  teams.value.forEach(t => {
    const m = t.team && t.team.match(/^(.+?)[\d]+组$/)
    if (m) classes.add(m[1])
  })
  return [...classes].sort()
})

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
    team_desc: '',
    class_name: '',
    tenure_mode: '',
    tenure_months: 3
  }
)

const stats = reactive({
  total_people: 0,
  total_records: 0,
  total_call_count: 0,
  total_work_duration: 0,
  total_ticket_count: 0,
  total_outbound: 0,
  total_sat_numerator: 0,
  total_sat_denominator: 0
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

watch(() => searchForm.team_desc, () => {
  if (searchForm.team_desc) searchForm.class_name = ''
  loadData()
})

watch(() => searchForm.class_name, () => {
  if (searchForm.class_name) searchForm.team_desc = ''
  loadData()
})

watch(viewMode, (val) => {
  if (val === 'class') classFilter.value = ''
})

function displayLabel(field) {
  const label = field.split('-').pop()
  if (label === '生成总量') return '提单量'
  return label
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
    const isMember = d.role !== '组长' && d.role !== '师傅'
    if (!teamMap[team]) {
      teamMap[team] = {
        count_all: 0, count_member: 0,
        total_calls_all: 0, total_calls_member: 0,
        total_duration: 0, total_work_duration_member: 0,
        total_ticket_count: 0,
        total_sat_numerator: 0, total_sat_denominator: 0,
        leaders: []
      }
    }
    const t = teamMap[team]
    t.count_all++
    if (d.role === '组长' && d.name) {
      t.leaders.push(d.name)
    }
    const calls = getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    t.total_calls_all += calls
    t.total_duration += getMetricValue(d, '呼入人工服务-人工服务-通话总时长(秒)') || 0
    t.total_ticket_count += getMetricValue(d, '呼入人工服务-工单-生成总量') || 0
    if (isMember) {
      t.count_member++
      t.total_calls_member += calls
      t.total_work_duration_member += getMetricValue(d, '总体-工作总时长(秒)') || 0
    }
    const verySat = getMetricValue(d, '呼入人工服务-满意度-非常满意量') || 0
    const sat = getMetricValue(d, '呼入人工服务-满意度-满意量') || 0
    const general = getMetricValue(d, '呼入人工服务-满意度-一般量') || 0
    const disSat = getMetricValue(d, '呼入人工服务-满意度-不满意量') || 0
    const veryDisSat = getMetricValue(d, '呼入人工服务-满意度-非常不满意量') || 0
    t.total_sat_numerator += verySat + sat
    t.total_sat_denominator += verySat + sat + general + disSat + veryDisSat
  })
  return Object.entries(teamMap)
    .map(([team, data]) => {
      const checkinHours = data.total_work_duration_member / 3600
      return {
        team,
        leader: data.leaders.filter((v, i, a) => a.indexOf(v) === i).join('、') || teamLeaders.value[team] || '',
        count: data.count_all,
        count_member: data.count_member,
        total_calls: data.total_calls_all,
        total_ticket_count: data.total_ticket_count,
        total_duration: data.total_duration,
        count: data.count_all,
        count_member: data.count_member,
        total_calls: data.total_calls_all,
        total_ticket_count: data.total_ticket_count,
        avg_calls_per_person_all: data.count_all > 0 ? +(data.total_calls_all / data.count_all).toFixed(1) : 0,
        avg_calls_per_person_member: data.count_member > 0 ? +(data.total_calls_member / data.count_member).toFixed(1) : 0,
        member_call_hourly_rate: checkinHours > 0 ? +(data.total_calls_member / checkinHours).toFixed(1) : 0,
        ti_dan_lv: data.total_calls_all > 0 ? data.total_ticket_count / data.total_calls_all : 0,
        avg_duration: data.total_calls_all > 0 ? +(data.total_duration / data.total_calls_all).toFixed(1) : 0,
        avg_satisfaction: data.total_sat_denominator > 0 ? data.total_sat_numerator / data.total_sat_denominator : null,
        total_sat_numerator: data.total_sat_numerator,
        total_sat_denominator: data.total_sat_denominator
      }
    })
    .sort((a, b) => b.total_calls - a.total_calls)
})

const teamChartData = computed(() => {
  const teamMap = {}
  tableData.value.forEach(d => {
    const team = d.team_desc || '未知班组'
    if (!teamMap[team]) {
      teamMap[team] = { value: 0, count: 0, totalDuration: 0, totalCalls: 0, totalTicket: 0 }
    }
    const t = teamMap[team]
    const calls = getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    t.value += calls
    t.count++
    t.totalCalls += calls
    t.totalTicket += getMetricValue(d, '呼入人工服务-工单-生成总量') || 0
    t.totalDuration += getMetricValue(d, '呼入人工服务-人工服务-通话总时长(秒)') || 0
  })
  return Object.entries(teamMap)
    .map(([name, data]) => ({
      name,
      value: Math.round(data.value),
      peopleCount: data.count,
      avgDuration: data.totalCalls > 0 ? +(data.totalDuration / data.totalCalls).toFixed(1) : 0,
      totalTicket: Math.round(data.totalTicket),
      tiDanLv: data.value > 0 ? data.totalTicket / data.value : 0
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
})

const teamMemberChartData = computed(() => {
  let team = ''
  if (filterType.value === 'team' && filterValue.value) {
    team = filterValue.value
  } else if (filterType.value === 'name' && filterValue.value) {
    const person = tableData.value.find(d => d.name === filterValue.value)
    if (person) team = person.team_desc
  } else if (searchForm.team_desc) {
    team = searchForm.team_desc
  }
  if (!team) return []
  const members = tableData.value.filter(d => d.team_desc === team)
  return members
    .map(d => ({
      name: d.name || '未知',
      value: getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    }))
    .sort((a, b) => b.value - a.value)
})

const totalCallSum = computed(() => {
  return teamRanking.value.reduce((s, d) => s + d.total_calls, 0)
})

function extractClass(team) {
  const m = team && team.match(/^(.+?)[\d]+组$/)
  return m ? m[1] : team
}

const classRanking = computed(() => {
  const classMap = {}
  teamRanking.value.forEach(t => {
    const cls = extractClass(t.team)
    if (!cls) return
    if (!classMap[cls]) {
      classMap[cls] = { count: 0, team_count: 0, total_calls: 0, total_ticket_count: 0, total_duration: 0, total_sat_numerator: 0, total_sat_denominator: 0 }
    }
    const c = classMap[cls]
    c.count += t.count
    c.team_count++
    c.total_calls += t.total_calls
    c.total_ticket_count += t.total_ticket_count
    c.total_duration += t.total_duration
    c.total_sat_numerator += t.total_sat_numerator || 0
    c.total_sat_denominator += t.total_sat_denominator || 0
  })
  return Object.entries(classMap)
    .map(([name, data]) => ({
      name,
      team_count: data.team_count,
      count: data.count,
      total_calls: data.total_calls,
      total_ticket_count: data.total_ticket_count,
      total_duration: data.total_duration,
      ti_dan_lv: data.total_calls > 0 ? data.total_ticket_count / data.total_calls : 0,
      avg_duration: data.total_calls > 0 ? +(data.total_duration / data.total_calls).toFixed(1) : 0,
      avg_satisfaction: data.total_sat_denominator > 0 ? data.total_sat_numerator / data.total_sat_denominator : null
    }))
    .sort((a, b) => b.total_calls - a.total_calls)
})

const classCallSum = computed(() => {
  return classRanking.value.reduce((s, d) => s + d.total_calls, 0)
})

const classFilteredRanking = computed(() => {
  if (!classFilter.value) return teamRanking.value
  return teamRanking.value.filter(t => extractClass(t.team) === classFilter.value)
})

const classFilteredChartData = computed(() => {
  if (!classFilter.value) return teamChartData.value
  return teamChartData.value.filter(t => extractClass(t.name) === classFilter.value)
})

const filteredCallSum = computed(() => {
  const data = classFilter.value ? classFilteredRanking.value : teamRanking.value
  return data.reduce((s, d) => s + d.total_calls, 0)
})

const averageCallDuration = computed(() => {
  let totalDuration = 0
  let totalCalls = 0
  tableData.value.forEach(d => {
    totalDuration += getMetricValue(d, '呼入人工服务-人工服务-通话总时长(秒)') || 0
    totalCalls += getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
  })
  if (totalCalls === 0) return 0
  return Math.round(totalDuration / totalCalls * 10) / 10
})

const totalTiDanLv = computed(() => {
  if (!stats.total_call_count) return 0
  return +(stats.total_ticket_count / stats.total_call_count * 100).toFixed(2)
})

const totalSatisfactionRate = computed(() => {
  if (!stats.total_sat_denominator) return 0
  return +(stats.total_sat_numerator / stats.total_sat_denominator * 100).toFixed(2)
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
const metricTargets = ref([])
const activeTargets = computed(() => metricTargets.value.filter(t => t.enabled !== false))

function getMetricStyle(fieldKey, value) {
  if (!activeTargets.value.length || value === null || value === undefined) return null
  const target = activeTargets.value.find(t => t.field === fieldKey)
  if (!target) return null
  let hit = false
  switch (target.operator) {
    case 'lt': hit = value < target.value; break
    case 'le': hit = value <= target.value; break
    case 'gt': hit = value > target.value; break
    case 'ge': hit = value >= target.value; break
  }
  return hit ? { color: target.color, fontWeight: 'bold' } : null
}

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
      } else if (item.rule_key === 'metric_targets') {
        metricTargets.value = item.rule_data.targets || []
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
    const workDuration = getMetricValue(row, '总体-工作总时长(秒)') || 0
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
      _call_hourly_rate: workDuration > 0 ? +(callCount / (workDuration / 3600)).toFixed(1) : 0,
      _ti_dan_lv: callCount > 0 ? ticketCount / callCount : 0,
      _call_salary: callSalary,
      _sat_salary: satSalary,
      _total_salary: totalSalary,
      _sat_diff: satDiffVal,
      ...gapValues
    }
  })
})

const SAT_FIELDS = [
  '呼入人工服务-满意度-非常满意量',
  '呼入人工服务-满意度-满意量',
  '呼入人工服务-满意度-一般量',
  '呼入人工服务-满意度-不满意量',
  '呼入人工服务-满意度-非常不满意量'
]

function satDenominator(row) {
  return SAT_FIELDS.reduce((s, f) => s + (getMetricValue(row, f) || 0), 0)
}

function satRate(row, fieldKeys) {
  const denom = satDenominator(row)
  if (denom <= 0) return null
  const num = fieldKeys.reduce((s, f) => s + (getMetricValue(row, f) || 0), 0)
  return +(num / denom * 100).toFixed(2)
}

const filterFields = computed(() => {
  const fields = []
  for (const f of allMetricFields.value) {
    if (f.isRate) {
      fields.push({
        key: f.field,
        label: f.label + '(%)',
        unit: 'percent',
        get: row => {
          const v = getMetricValue(row, f.field)
          return v === null || v === undefined ? null : +(v * 100).toFixed(2)
        }
      })
    } else {
      fields.push({ key: f.field, label: f.label, unit: 'number', get: row => getMetricValue(row, f.field) })
    }
  }
  fields.push({
    key: '__sat_rate', label: '满意率(%)', unit: 'percent',
    get: row => satRate(row, ['呼入人工服务-满意度-非常满意量', '呼入人工服务-满意度-满意量'])
  })
  fields.push({
    key: '__dis_sat_rate', label: '不满意率(%)', unit: 'percent',
    get: row => satRate(row, ['呼入人工服务-满意度-不满意量', '呼入人工服务-满意度-非常不满意量'])
  })
  fields.push({
    key: '__very_dis_sat_rate', label: '非常不满意率(%)', unit: 'percent',
    get: row => satRate(row, ['呼入人工服务-满意度-非常不满意量'])
  })
  fields.push({
    key: '__general_rate', label: '一般率(%)', unit: 'percent',
    get: row => satRate(row, ['呼入人工服务-满意度-一般量'])
  })
  fields.push({
    key: '__very_sat_rate', label: '非常满意率(%)', unit: 'percent',
    get: row => satRate(row, ['呼入人工服务-满意度-非常满意量'])
  })
  fields.push({ key: '_ti_dan_lv', label: '提单率(%)', unit: 'percent', get: row => (row._ti_dan_lv ?? null) === null ? null : +(row._ti_dan_lv * 100).toFixed(2) })
  fields.push({ key: '_call_hourly_rate', label: '接话小时量', unit: 'number', get: row => row._call_hourly_rate ?? null })
  if (userStore.hasPermission('workload_report.view_call_salary')) {
    fields.push({ key: '_call_salary', label: '接话绩效(预测)', unit: 'number', get: row => row._call_salary ?? null })
  }
  if (userStore.hasPermission('workload_report.view_sat_salary')) {
    fields.push({ key: '_sat_salary', label: '满意度绩效(预测)', unit: 'number', get: row => row._sat_salary ?? null })
  }
  if (userStore.hasPermission('workload_report.view_total_salary')) {
    fields.push({ key: '_total_salary', label: '合计绩效(预测)', unit: 'number', get: row => row._total_salary ?? null })
  }
  if (userStore.hasPermission('workload_report.view_sat_diff')) {
    fields.push({ key: '_sat_diff', label: '满意度差额', unit: 'number', get: row => row._sat_diff ?? null })
  }
  for (const target of salaryCfg.gapTargets) {
    fields.push({ key: `gap_${target}`, label: `话务量差额(${target})`, unit: 'number', get: row => row[`gap_${target}`] ?? null })
  }
  return fields
})

const fieldFilter = useFieldFilter(filterFields, { persistKey: 'workload-report-field-filter' })

const dataLoading = ref(false)

function handleFieldFilterChange() {
  currentPage.value = 1
}

const paginatedData = computed(() => {
  let data = fieldFilter.filtered(enrichedData.value)
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
  const activeTeam = filterType.value === 'team' ? filterValue.value : searchForm.team_desc
  if (activeTeam) {
    const data = teamMemberChartData.value
    if (!data.length) return {}
    const options = createBarOptions(
      data.map(d => d.name),
      data.map(d => d.value),
      `${activeTeam} 成员产量`,
      '姓名',
      '通话量'
    )
    options.xAxis.axisLabel = { rotate: 45, interval: 0 }
    options.grid.bottom = '25%'
    return options
  }
  if (classFilter.value) {
    const data = classFilteredChartData.value
    if (!data.length) return {}
    return createPieOptions(data, `${classFilter.value} 产量占比`, undefined, '产量')
  }
  if (viewMode.value === 'class' && classRanking.value.length) {
    return createPieOptions(
      classRanking.value.map(r => ({ name: r.name, value: r.total_calls, peopleCount: r.count })),
      '班级产量占比',
      undefined,
      '产量'
    )
  }
  if (!teamChartData.value.length) return {}
  return createPieOptions(teamChartData.value, '班组产量占比', undefined, '产量')
})


function handleSortChange({ prop, order }) {
  sortBy.value = prop || ''
  sortOrder.value = order || ''
  currentPage.value = 1
}

function handleExport() {
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
  if (searchForm.class_name) params.team_prefix = searchForm.class_name
  if (searchForm.tenure_mode) {
    params.tenure_mode = searchForm.tenure_mode
    params.tenure_months = searchForm.tenure_months
  }
  downloadBlob('/workloads/report/export', params, `workload_report.csv`)
}

function handleExportFiltered() {
  const data = fieldFilter.filtered(enrichedData.value)
  if (!data.length) {
    ElMessage.warning('没有筛选数据可供导出')
    return
  }

  const columns = buildScreenshotColumns(visibleMetricColumns.value, salaryCfg.gapTargets)
  const headers = columns.map(c => c.label)

  const rows = data.map(row =>
    columns.map(col => {
      const cell = formatScreenshotCell(row, col, activeTargets.value, 0)
      return cell.text
    })
  )

  const csvContent = [headers, ...rows].map(line =>
    line.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')
  ).join('\n')

  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  let filename = 'workload_report_filtered.csv'
  if (searchForm.team_desc) {
    filename = `${searchForm.team_desc}_工作量报表.csv`
  } else if (searchForm.class_name) {
    filename = `${searchForm.class_name}_工作量报表.csv`
  }
  link.download = filename
  link.href = URL.createObjectURL(blob)
  link.click()
  URL.revokeObjectURL(link.href)
  ElMessage.success('导出筛选成功')
}

function buildScreenshotColumns(visibleMetricCols, gapTargets) {
  const cols = [
    { prop: '_index', label: '排名', width: 55 },
    { prop: 'account', label: '账号', width: 110 },
    { prop: 'name', label: '姓名', width: 80 },
    { prop: 'team_desc', label: '班组', width: 140 },
    { prop: 'date_count', label: '天数', width: 60 },
    ...visibleMetricCols.map(c => ({ prop: c.field, label: c.label, width: c.width, isRate: c.isRate })),
    { prop: '_ti_dan_lv', label: '提单率', width: 85, isRate: true },
    { prop: '_call_hourly_rate', label: '接话小时量', width: 90 },
  ]
  if (userStore.hasPermission('workload_report.view_call_salary')) {
    cols.push({ prop: '_call_salary', label: '接话绩效(预测)', width: 100 })
  }
  if (userStore.hasPermission('workload_report.view_sat_salary')) {
    cols.push({ prop: '_sat_salary', label: '满意度绩效(预测)', width: 100 })
  }
  if (userStore.hasPermission('workload_report.view_total_salary')) {
    cols.push({ prop: '_total_salary', label: '合计绩效(预测)', width: 100 })
  }
  if (userStore.hasPermission('workload_report.view_gap')) {
    gapTargets.forEach(target => {
      cols.push({ prop: `gap_${target}`, label: `话务量差额(${target})`, width: 110 })
    })
  }
  if (userStore.hasPermission('workload_report.view_sat_diff')) {
    cols.push({ prop: '_sat_diff', label: '满意度差额', width: 100 })
  }
  return cols
}

function getScreenshotMetricStyle(fieldKey, value, targets) {
  if (!targets || !targets.length || value === null || value === undefined) return null
  const target = targets.find(t => t.field === fieldKey)
  if (!target) return null
  let hit = false
  switch (target.operator) {
    case 'lt': hit = value < target.value; break
    case 'le': hit = value <= target.value; break
    case 'gt': hit = value > target.value; break
    case 'ge': hit = value >= target.value; break
  }
  return hit ? { color: target.color, fontWeight: 'bold' } : null
}

function formatScreenshotCell(row, col, activeTargets, rowIndex) {
  if (col.prop === '_index') {
    return { text: String(rowIndex + 1), style: null }
  }
  let val
  if (col.prop === 'account' || col.prop === 'name' || col.prop === 'emp_no' || col.prop === 'team_desc' || col.prop === 'date_count') {
    val = row[col.prop]
  } else if (col.prop.startsWith('_') || col.prop.startsWith('gap_')) {
    val = row[col.prop]
  } else {
    val = getMetricValue(row, col.prop)
  }
  let text
  if (val === null || val === undefined) {
    text = '-'
  } else if (col.isRate) {
    const num = typeof val === 'number' ? val : parseFloat(val)
    text = isNaN(num) ? '-' : (num * 100).toFixed(2) + '%'
  } else if (typeof val === 'number') {
    text = Number.isInteger(val) ? String(val) : val.toFixed(1)
  } else {
    text = String(val)
  }
  let style = null
  if (text !== '-') {
    const numericVal = typeof val === 'number' ? val : (val !== null && val !== undefined ? parseFloat(val) : null)
    if (numericVal !== null && !isNaN(numericVal)) {
      style = getScreenshotMetricStyle(col.prop, numericVal, activeTargets)
    }
  }
  return { text, style }
}

function buildScreenshotHtml(title, periodInfo, filterInfo, columns, rows, now) {
  const pad = n => String(n).padStart(2, '0')
  const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
  const colGroup = columns.map(c => `<col style="width: ${c.width}px">`).join('')
  const headerRow = columns.map(c => `<th style="padding: 8px 6px; border: 1px solid #d9d9d9; white-space: nowrap; font-weight: 600;">${c.label}</th>`).join('')
  const bodyRows = rows.map((r, i) => {
    const bg = i % 2 === 0 ? '#fafafa' : '#ffffff'
    const cells = r.cells.map(c => {
      const extraStyle = c.style ? ` color: ${c.style.color}; font-weight: ${c.style.fontWeight};` : ''
      return `<td style="padding: 6px; border: 1px solid #e8e8e8; white-space: nowrap; background: ${bg};${extraStyle}">${c.text}</td>`
    }).join('')
    return `<tr>${cells}</tr>`
  }).join('')
  return `<div style="padding: 30px 30px 20px; font-family: 'Microsoft YaHei', 'PingFang SC', -apple-system, sans-serif; color: #333; min-width: ${columns.reduce((s, c) => s + c.width, 0) + 60}px;">
    <div style="text-align: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #409eff;">
      <h1 style="font-size: 20px; margin: 0 0 8px 0; color: #1d1d1f;">${title}</h1>
      <div style="font-size: 13px; color: #666; display: flex; justify-content: center; gap: 24px;">
        ${periodInfo ? `<span style="background: #f0f5ff; padding: 2px 10px; border-radius: 4px;">日期: ${periodInfo}</span>` : ''}
        ${filterInfo ? `<span style="background: #f0f5ff; padding: 2px 10px; border-radius: 4px;">${filterInfo}</span>` : ''}
      </div>
    </div>
    <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center;">
      ${colGroup}
      <thead>
        <tr style="background: #409eff; color: #fff;">${headerRow}</tr>
      </thead>
      <tbody>${bodyRows || '<tr><td colspan="' + columns.length + '" style="padding: 30px; text-align: center; color: #999;">暂无数据</td></tr>'}</tbody>
    </table>
    <div style="text-align: right; font-size: 11px; color: #b0b0b0; margin-top: 12px; padding-top: 8px; border-top: 1px solid #eee;">
      生成时间: ${dateStr}
    </div>
  </div>`
}

async function handleScreenshot() {
  let data = fieldFilter.filtered(enrichedData.value)
  if (!data.length) {
    ElMessage.warning('没有数据可供导出')
    return
  }

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

  let periodInfo = ''
  if (searchForm.type === 'day' && searchForm.date) {
    periodInfo = searchForm.date
  } else if (searchForm.type === 'month' && searchForm.month) {
    periodInfo = searchForm.month
  } else if (searchForm.type === 'range' && searchForm.start_date && searchForm.end_date) {
    periodInfo = `${searchForm.start_date} ~ ${searchForm.end_date}`
  }

  let title = '工作量报表'
  if (searchForm.team_desc) {
    title = `${searchForm.team_desc} ${title}`
  } else if (filterType.value === 'team' && filterValue.value) {
    title = `${filterValue.value} ${title}`
  } else if (searchForm.class_name) {
    title = `${searchForm.class_name} ${title}`
  } else if (classFilter.value) {
    title = `${classFilter.value} ${title}`
  }

  const columns = buildScreenshotColumns(visibleMetricColumns.value, salaryCfg.gapTargets)
  const targets = activeTargets.value
  const rows = data.map((row, i) => ({
    cells: columns.map(col => formatScreenshotCell(row, col, targets, i))
  }))

  const container = document.createElement('div')
  container.className = 'screenshot-container'
  container.innerHTML = buildScreenshotHtml(title, periodInfo, null, columns, rows, new Date())
  container.style.cssText = 'position: fixed; left: -9999px; top: 0; z-index: -1;'
  document.body.appendChild(container)

  screenshotLoading.value = true
  try {
    const canvas = await html2canvas(container, {
      scale: 2,
      backgroundColor: '#ffffff',
      useCORS: true,
      logging: false,
      onclone: () => {}
    })
    const link = document.createElement('a')
    link.download = `工作量报表_${periodInfo || '报表'}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
    ElMessage.success('截图导出成功')
  } catch (e) {
    ElMessage.error('截图导出失败: ' + (e.message || '未知错误'))
  } finally {
    screenshotLoading.value = false
    document.body.removeChild(container)
  }
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

function handlePieClick(params) {
  if (!params.name) return
  if (filterType.value === 'team') {
    clearFilter()
    return
  }
  if (viewMode.value === 'class') {
    classFilter.value = params.name
    viewMode.value = 'team'
    return
  }
  filterType.value = 'team'
  filterValue.value = params.name
  currentPage.value = 1
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

async function loadTeams() {
  try {
    const res = await api.get('/employees/teams')
    teams.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

async function loadTeamLeaders() {
  try {
    const res = await api.get('/employees/leaders')
    const map = {}
    ;(res.data || []).forEach(item => {
      if (item.team) map[item.team] = item.leader
    })
    teamLeaders.value = map
  } catch (e) {
    console.error(e)
  }
}

async function loadData() {
  clearFilter()
  dataLoading.value = true
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
    if (searchForm.class_name) params.team_prefix = searchForm.class_name
    if (searchForm.tenure_mode) {
      params.tenure_mode = searchForm.tenure_mode
      params.tenure_months = searchForm.tenure_months
    }

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
    let satNum = 0, satDen = 0
    data.forEach(d => {
      const vs = getMetricValue(d, '呼入人工服务-满意度-非常满意量') || 0
      const s = getMetricValue(d, '呼入人工服务-满意度-满意量') || 0
      const g = getMetricValue(d, '呼入人工服务-满意度-一般量') || 0
      const ds = getMetricValue(d, '呼入人工服务-满意度-不满意量') || 0
      const vds = getMetricValue(d, '呼入人工服务-满意度-非常不满意量') || 0
      satNum += vs + s
      satDen += vs + s + g + ds + vds
    })
    stats.total_sat_numerator = satNum
    stats.total_sat_denominator = satDen
    tableData.value = data

    if (data.length === 0) {
      const range = params.start_date
        ? params.start_date + (params.end_date !== params.start_date ? ' ~ ' + params.end_date : '')
        : (params.year_month || '当前')
      ElMessage.info(`所选日期(${range})没有工作量数据，请调整查询条件`)
    }
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    dataLoading.value = false
  }
}

async function openDetail(row) {
  drawerTitle.value = `${row.name}（${row.account}）工作量明细`
  personalRecords.value = []
  drawerVisible.value = true

  try {
    const { startDate, endDate } = getWorkloadDetailDateRange(searchForm)
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
  loadTeams()
  loadTeamLeaders()
  loadData()
  loadMetricsFields()
  workloadAnnotator.loadAnnotations().then(m => { workloadAnnMap.value = m })
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stats-row {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}
.stats-row :deep(.el-statistic__head) {
  font-size: 12px;
  line-height: 1.2;
  margin-bottom: 2px;
}
.stats-row :deep(.el-statistic__content) {
  font-size: 18px;
  line-height: 1.4;
}
</style>
