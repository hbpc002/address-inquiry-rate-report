<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.employeeCount }}</div>
            <div class="stat-label">员工总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.todayAttendance }}</div>
            <div class="stat-label">今日出勤</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.todayLate }}</div>
            <div class="stat-label">今日迟到</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.todayAbsent }}</div>
            <div class="stat-label">今日缺勤</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>今日考勤状态分布</span>
          </template>
          <Echart :options="attendancePieOptions" :height="300" @click="handleAttendanceClick" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>各部门人数</span>
          </template>
          <Echart :options="deptBarOptions" :height="300" @click="handleDeptClick" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>各班组人数</span>
          </template>
          <Echart :options="teamBarOptions" :height="300" @click="handleTeamClick" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>班组出勤排名</span>
          </template>
          <Echart :options="rankingOptions" :height="300" @click="handleRankingClick" />
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>快速操作</span>
      </template>
      <el-space wrap>
        <el-button type="primary" @click="$router.push('/employees')">员工管理</el-button>
        <el-button type="success" @click="$router.push('/schedules')">排班管理</el-button>
        <el-button type="warning" @click="$router.push('/checkins')">导入签到</el-button>
        <el-button type="info" @click="$router.push('/reports')">考勤报表</el-button>
      </el-space>
    </el-card>

    <el-dialog v-model="detailDialogVisible" :title="detailTitle" width="800px">
      <el-table :data="detailData" border stripe max-height="400">
        <el-table-column prop="emp_no" label="工号" width="100" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="team" label="班组" width="120" />
        <el-table-column prop="dept" label="部门" width="120" />
        <el-table-column v-if="detailType === 'attendance'" prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="detailType === 'attendance'" prop="late_minutes" label="迟到(分)" width="80" />
        <el-table-column v-if="detailType === 'dept' || detailType === 'team'" prop="status" label="在职状态" width="100">
          <template #default>
            <el-tag type="success">在职</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../stores/user'
import Echart from '../components/Echart.vue'
import { createPieOptions, createBarOptions, createHorizontalBarOptions } from '../utils/echarts'

const stats = ref({
  employeeCount: 0,
  todayAttendance: 0,
  todayLate: 0,
  todayAbsent: 0
})

const depts = ref([])
const teams = ref([])
const rankingData = ref([])
const todayReports = ref([])

const detailDialogVisible = ref(false)
const detailTitle = ref('')
const detailData = ref([])
const detailType = ref('')

const attendancePieOptions = computed(() => {
  const total = stats.value.employeeCount || 1
  const data = [
    { name: '正常', value: stats.value.todayAttendance || 0 },
    { name: '迟到', value: stats.value.todayLate || 0 },
    { name: '缺勤', value: stats.value.todayAbsent || 0 }
  ]
  return createPieOptions(data, '', ['#67c23a', '#e6a23c', '#f56c6c'])
})

const deptBarOptions = computed(() => {
  const data = depts.value.slice(0, 10)
  return createBarOptions(data.map(d => d.dept), data.map(d => d.count), '', '部门', '人数')
})

const teamBarOptions = computed(() => {
  const data = teams.value.slice(0, 10)
  return createBarOptions(data.map(t => t.team), data.map(t => t.count), '', '班组', '人数')
})

const rankingOptions = computed(() => {
  const data = [...rankingData.value].sort((a, b) => b.avg_attendance - a.avg_attendance).slice(0, 8)
  const names = data.map(d => d.team)
  const rates = data.map(d => Math.round(d.avg_attendance * 100))
  return createHorizontalBarOptions(names, rates, '', '班组', '出勤率(%)')
})

function getStatusType(status) {
  const map = { '正常': 'success', '迟到': 'warning', '缺勤': 'danger', '早退': 'warning', '请假': 'info', '公休': '' }
  return map[status] || 'info'
}

async function loadStats() {
  try {
    const res = await api.get('/system/stats')
    stats.value = res.data
  } catch (e) {
    stats.value = { employeeCount: 0, todayAttendance: 0, todayLate: 0, todayAbsent: 0 }
  }
}

async function loadDepts() {
  try {
    const res = await api.get('/system/departments')
    depts.value = res.data || []
  } catch (e) {
    depts.value = []
  }
}

async function loadTeams() {
  try {
    const res = await api.get('/system/teams')
    teams.value = res.data || []
  } catch (e) {
    teams.value = []
  }
}

async function loadRanking() {
  try {
    const now = new Date()
    const yearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const res = await api.get('/reports/team-ranking', { params: { year_month: yearMonth } })
    rankingData.value = res.data || []
  } catch (e) {
    rankingData.value = []
  }
}

async function loadTodayReports() {
  try {
    const today = new Date().toISOString().slice(0, 10)
    const res = await api.get('/reports/daily', { params: { schedule_date: today } })
    todayReports.value = res.data.items || []
  } catch (e) {
    todayReports.value = []
  }
}

function handleAttendanceClick(params) {
  const statusMap = { '正常': '正常', '迟到': '迟到', '缺勤': '缺勤' }
  const status = statusMap[params.name]
  if (!status) return

  const filtered = todayReports.value.filter(r => r.status === status)
  detailTitle.value = `${params.name}人员列表 (${filtered.length}人)`
  detailData.value = filtered
  detailType.value = 'attendance'
  detailDialogVisible.value = true
}

function handleDeptClick(params) {
  const deptName = params.name
  const filtered = todayReports.value.filter(r => r.dept === deptName)
  detailTitle.value = `${deptName}员工列表 (${filtered.length}人)`
  detailData.value = filtered.length ? filtered : depts.value.filter(d => d.dept === deptName).map(d => ({
    emp_no: '-', name: `${d.count}人`, team: '-', dept: deptName, status: '在职'
  }))
  detailType.value = 'dept'
  detailDialogVisible.value = true
}

function handleTeamClick(params) {
  const teamName = params.name
  const filtered = todayReports.value.filter(r => r.team === teamName)
  detailTitle.value = `${teamName}员工列表 (${filtered.length}人)`
  detailData.value = filtered.length ? filtered : teams.value.filter(t => t.team === teamName).map(t => ({
    emp_no: '-', name: `${t.count}人`, team: teamName, dept: '-', status: '在职'
  }))
  detailType.value = 'team'
  detailDialogVisible.value = true
}

function handleRankingClick(params) {
  const teamName = params.name
  const teamData = rankingData.value.find(r => r.team === teamName)
  if (teamData) {
    const filtered = todayReports.value.filter(r => r.team === teamName)
    detailTitle.value = `${teamName}详情 (${teamData.emp_count}人, 出勤率${Math.round(teamData.avg_attendance * 100)}%)`
    detailData.value = filtered.length ? filtered : [{ emp_no: '-', name: `${teamData.emp_count}人`, team: teamName, dept: '-', status: '在职' }]
  } else {
    detailTitle.value = `${teamName}详情`
    detailData.value = []
  }
  detailType.value = 'ranking'
  detailDialogVisible.value = true
}

onMounted(() => {
  loadStats()
  loadDepts()
  loadTeams()
  loadRanking()
  loadTodayReports()
})
</script>

<style scoped>
.dashboard {
  width: 100%;
}

.stat-card {
  text-align: center;
  padding: 20px 0;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409EFF;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 10px;
}
</style>