<template>
  <div class="checkin-report">
    <el-card>
      <template #header>
        <span>签入签出报表</span>
      </template>

      <el-form inline>
        <el-form-item label="查询方式">
          <el-radio-group v-model="searchForm.type" @change="handleTypeChange">
            <el-radio label="day">按天</el-radio>
            <el-radio label="month">按月</el-radio>
            <el-radio label="range">自定义</el-radio>
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
        <el-form-item label="工号">
          <el-input v-model="searchForm.emp_no" placeholder="请输入工号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="searchForm.team" placeholder="全部班组" clearable filterable style="width: 140px">
            <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-row :gutter="20" class="stats-row">
        <el-col :span="6">
          <el-statistic title="签入人次" :value="stats.total_checkins" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="总人数" :value="stats.emp_count" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="总时长" :value="stats.total_hours" :precision="1">
            <template #suffix>小时</template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="平均时长" :value="stats.avg_hours" :precision="1">
            <template #suffix>小时</template>
          </el-statistic>
        </el-col>
      </el-row>

      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 20px">
        <el-col :span="12">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center">
              <span style="font-size: 14px; color: #606266">员工工时排名</span>
              <el-radio-group v-model="chartType" size="small">
                <el-radio-button value="bar">柱状图</el-radio-button>
                <el-radio-button value="line">折线图</el-radio-button>
              </el-radio-group>
            </div>
            <Echart :options="hoursChartOptions" :height="280" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; font-size: 14px; color: #606266">员工签入次数排名</div>
            <Echart :options="checkinCountOptions" :height="300" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 20px">
        <el-col :span="24">
          <el-card shadow="hover">
            <Echart :options="deptHoursOptions" :height="300" />
          </el-card>
        </el-col>
      </el-row>

      <el-table :data="paginatedData" border stripe show-summary>
        <el-table-column prop="emp_no" label="账号" width="100" />
        <el-table-column prop="name" label="用户名" width="100" />
        <el-table-column prop="dept" label="所属部门" min-width="150" />
        <el-table-column prop="team" label="班组" width="100" />
        <el-table-column prop="checkin_count" label="签入次数" width="80" sortable />
        <el-table-column prop="total_hours" label="工作时长" width="80" sortable>
          <template #default="{ row }">
            {{ row.total_hours.toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column label="签入明细" min-width="400">
          <template #default="{ row }">
            <template v-if="row.checkins && row.checkins.length">
              <div v-for="(c, idx) in row.checkins" :key="idx" style="display: inline-block; margin: 2px 8px 2px 0;">
                <el-tag size="small">{{ idx + 1 }}: {{ c.checkin_time || '-' }} → {{ c.checkout_time || '-' }}</el-tag>
                <span style="margin-left: 4px; font-size: 12px; color: #666;">
                  ({{ c.duration.toFixed(1) }}h)
                </span>
              </div>
            </template>
            <span v-else>-</span>
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'
import Echart from '../components/Echart.vue'
import { createPieOptions, createBarOptions, createLineOptions, createHorizontalBarOptions } from '../utils/echarts'

const tableData = ref([])
const teams = ref([])
const currentPage = ref(1)
const pageSize = ref(20)

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return tableData.value.slice(start, end)
})

const searchForm = reactive({
  type: 'day',
  date: '',
  month: '',
  start_date: '',
  end_date: '',
  name: '',
  emp_no: '',
  team: ''
})

const stats = reactive({
  total_checkins: 0,
  emp_count: 0,
  total_hours: 0,
  avg_hours: 0
})

const chartType = ref('bar')

const hoursChartOptions = computed(() => {
  if (!tableData.value.length) return {}
  const data = [...tableData.value].sort((a, b) => b.total_hours - a.total_hours).slice(0, 10)
  if (chartType.value === 'line') {
    return createLineOptions(data.map(d => d.name), data.map(d => d.total_hours.toFixed(1)), '员工工时排名', '姓名', '工时(h)')
  }
  return createBarOptions(data.map(d => d.name), data.map(d => d.total_hours.toFixed(1)), '员工工时排名', '姓名', '工时(h)')
})

const checkinCountOptions = computed(() => {
  if (!tableData.value.length) return {}
  const data = [...tableData.value].sort((a, b) => a.checkin_count - b.checkin_count).slice(-10)
  return createHorizontalBarOptions(data.map(d => d.name), data.map(d => d.checkin_count), '员工签入次数排名', '姓名', '签入次数')
})

const deptHoursOptions = computed(() => {
  if (!tableData.value.length) return {}
  const teamMap = {}
  tableData.value.forEach(d => {
    const team = d.team || '未知班组'
    if (!teamMap[team]) teamMap[team] = 0
    teamMap[team] += d.total_hours
  })
  const data = Object.entries(teamMap).map(([name, value]) => ({ name, value: Math.round(value) }))
    .sort((a, b) => b.value - a.value).slice(0, 8)
  return createPieOptions(data, '班组工时分布')
})

function handleTypeChange() {
  const today = new Date().toISOString().slice(0, 10)
  const now = new Date()
  
  if (searchForm.type === 'day') {
    searchForm.date = today
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
    searchForm.end_date = today
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

async function loadData() {
  try {
    const params = {}
    
    if (searchForm.type === 'day' && searchForm.date) {
      params.date = searchForm.date
    } else if (searchForm.type === 'month' && searchForm.month) {
      params.year_month = searchForm.month
    } else if (searchForm.type === 'range' && searchForm.start_date && searchForm.end_date) {
      params.start_date = searchForm.start_date
      params.end_date = searchForm.end_date
    }
    
    if (searchForm.name) params.name = searchForm.name
    if (searchForm.emp_no) params.emp_no = searchForm.emp_no
    if (searchForm.team) params.team = searchForm.team
    
    const res = await api.get('/checkins/report', { params })
    
    stats.total_checkins = res.data.stats.total_checkins
    stats.emp_count = res.data.stats.emp_count
    stats.total_hours = res.data.stats.total_hours
    stats.avg_hours = res.data.stats.avg_hours
    tableData.value = res.data.items || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  handleTypeChange()
  loadTeams()
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