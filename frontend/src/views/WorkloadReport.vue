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
        <el-col :span="12">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center">
              <span style="font-size: 14px; color: #606266">呼入通话量排名 TOP10</span>
            </div>
            <Echart :options="callCountChartOptions" height="280px" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; font-size: 14px; color: #606266">工单量排名 TOP10</div>
            <Echart :options="ticketChartOptions" height="280px" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 20px">
        <el-col :span="24">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; font-size: 14px; color: #606266">班组工时占比</div>
            <Echart :options="teamChartOptions" height="300px" />
          </el-card>
        </el-col>
      </el-row>

      <el-table :data="paginatedData" border stripe max-height="calc(100vh - 350px)">
        <el-table-column prop="account" label="账号" width="110" />
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column prop="emp_no" label="工号" width="80" />
        <el-table-column prop="team_desc" label="班组" min-width="140" />
        <el-table-column prop="date_count" label="天数" width="60" sortable />
        <el-table-column label="通话次数" width="80" sortable>
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-人工服务-通话次数') }}
          </template>
        </el-table-column>
        <el-table-column label="通话总时长" width="90" sortable>
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-人工服务-通话总时长(秒)') }}
          </template>
        </el-table-column>
        <el-table-column label="通话均长" width="80" sortable>
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-人工服务-通话均长(秒)') }}
          </template>
        </el-table-column>
        <el-table-column label="整理总时长" width="90" sortable>
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-人工服务-服务后整理总时长(秒)') }}
          </template>
        </el-table-column>
        <el-table-column label="工单总量" width="70" sortable>
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-工单-生成总量') }}
          </template>
        </el-table-column>
        <el-table-column label="满意率" width="70" sortable>
          <template #default="{ row }">
            {{ formatMetric(row, '人工服务-满意度-满意率', '%') }}
          </template>
        </el-table-column>
        <el-table-column label="解决率" width="70" sortable>
          <template #default="{ row }">
            {{ formatMetric(row, '呼入人工服务-解决率-解决率', '%') }}
          </template>
        </el-table-column>
        <el-table-column label="呼出呼叫量" width="80" sortable>
          <template #default="{ row }">
            {{ formatMetric(row, '呼出服务-人工呼出呼叫量') }}
          </template>
        </el-table-column>
        <el-table-column label="工时利用率" width="80" sortable>
          <template #default="{ row }">
            {{ formatMetric(row, '总体-工时利用率', '%') }}
          </template>
        </el-table-column>
        <el-table-column label="示忙次数" width="70" sortable>
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
        :total="tableData.length"
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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'
import Echart from '../components/Echart.vue'
import { createBarOptions, createPieOptions, CHART_COLORS } from '../utils/echarts'
import { getYesterday } from '../utils/date'

const tableData = ref([])
const teams = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const drawerVisible = ref(false)
const drawerTitle = ref('')
const personalRecords = ref([])

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

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return tableData.value.slice(start, end)
})

function formatMetric(row, field, suffix = '') {
  const val = row.aggregated_metrics?.[field]
  if (val === null || val === undefined) return '-'
  if (typeof val === 'number') {
    if (Number.isInteger(val)) return val + suffix
    return val.toFixed(1) + suffix
  }
  return val + suffix
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

const callCountChartOptions = computed(() => {
  if (!tableData.value.length) return {}
  const data = [...tableData.value]
    .sort((a, b) => (b.aggregated_metrics?.['呼入人工服务-人工服务-通话次数'] || 0) - (a.aggregated_metrics?.['呼入人工服务-人工服务-通话次数'] || 0))
    .slice(0, 10)
  return createBarOptions(
    data.map(d => d.name || d.account),
    data.map(d => (d.aggregated_metrics?.['呼入人工服务-人工服务-通话次数'] || 0).toFixed(0)),
    '呼入通话量排名',
    '姓名',
    '通话次数'
  )
})

const ticketChartOptions = computed(() => {
  if (!tableData.value.length) return {}
  const data = [...tableData.value]
    .sort((a, b) => (b.aggregated_metrics?.['呼入人工服务-工单-生成总量'] || 0) - (a.aggregated_metrics?.['呼入人工服务-工单-生成总量'] || 0))
    .slice(0, 10)
  return createBarOptions(
    data.map(d => d.name || d.account),
    data.map(d => (d.aggregated_metrics?.['呼入人工服务-工单-生成总量'] || 0).toFixed(0)),
    '工单量排名',
    '姓名',
    '工单量'
  )
})

const teamChartOptions = computed(() => {
  if (!tableData.value.length) return {}
  const teamMap = {}
  tableData.value.forEach(d => {
    const team = d.team_desc || '未知班组'
    if (!teamMap[team]) teamMap[team] = 0
    teamMap[team] += d.aggregated_metrics?.['总体-工作总时长(秒)'] || 0
  })
  const data = Object.entries(teamMap)
    .map(([name, value]) => ({ name, value: Math.round(value) }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
  return createPieOptions(data, '班组工时占比')
})

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
    const params = { workload_date: startDate ? undefined : undefined }
    if (startDate && endDate) {
      params.start_date = startDate
      params.end_date = endDate
    }
    params.account = row.account
    const res = await api.get('/workloads', { params: { ...params, limit: 100 } })
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