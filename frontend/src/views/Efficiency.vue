<template>
  <div class="efficiency">
    <el-card>
      <template #header>
        <span>人员效能监控</span>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="员工效能" name="employee">
          <el-form inline>
            <el-form-item label="月份">
              <el-date-picker v-model="searchEmp.year_month" type="month" value-format="YYYY-MM" />
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="searchEmp.dept" placeholder="全部部门" clearable filterable>
                <el-option v-for="d in depts" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchEmp.team" placeholder="全部班组" clearable filterable>
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadEmployeeEfficiency">查询</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" class="stats-row">
            <el-col :span="4">
              <el-statistic title="员工人数" :value="empStats.total" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="平均出勤率" :value="empStats.avgAttendance" :precision="1" suffix="%" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="平均工时效率" :value="empStats.avgEfficiency" :precision="1" suffix="%" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="迟到人数" :value="empStats.lateCount" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="缺勤人数" :value="empStats.absentCount" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="加班人数" :value="empStats.overtimeCount" />
            </el-col>
          </el-row>

          <el-row :gutter="20" v-if="empData.length" style="margin-bottom: 20px">
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="empEfficiencyOptions" :height="280" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="empAttendanceOptions" :height="280" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="empData" border stripe>
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="100" />
            <el-table-column prop="dept" label="部门" width="100" />
            <el-table-column prop="attendance_rate" label="出勤率" width="80" sortable>
              <template #default="{ row }">
                <span :class="getRateClass(row.attendance_rate)">{{ row.attendance_rate }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="efficiency_rate" label="工时效率" width="80" sortable>
              <template #default="{ row }">
                <span :class="getRateClass(row.efficiency_rate)">{{ row.efficiency_rate }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="scheduled_hours" label="计划工时" width="80" sortable />
            <el-table-column prop="actual_hours" label="实际工时" width="80" sortable />
            <el-table-column prop="overtime_hours" label="加班" width="60" sortable>
              <template #default="{ row }">
                <span :class="{'text-success': row.overtime_hours > 0}">{{ row.overtime_hours }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="late_days" label="迟到" width="60" sortable>
              <template #default="{ row }">
                <span :class="{'text-warning': row.late_days > 0}">{{ row.late_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="absent_days" label="缺勤" width="60" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.absent_days > 0}">{{ row.absent_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="work_days" label="出勤天数" width="80" sortable />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" link @click="showEmpDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="效能预警" name="warning">
          <el-form inline>
            <el-form-item label="预警类型">
              <el-select v-model="searchWarn.type" placeholder="全部">
                <el-option label="迟到预警" value="late" />
                <el-option label="缺勤预警" value="absent" />
                <el-option label="效率预警" value="efficiency" />
              </el-select>
            </el-form-item>
            <el-form-item label="月份">
              <el-date-picker v-model="searchWarn.year_month" type="month" value-format="YYYY-MM" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadWarnings">查询</el-button>
            </el-form-item>
          </el-form>

          <el-alert v-if="warningData.length" :title="`共 ${warningData.length} 人需要关注`" type="warning" style="margin-bottom: 20px" />

          <el-table :data="warningData" border stripe>
            <el-table-column type="index" label="序号" width="60" />
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="100" />
            <el-table-column prop="dept" label="部门" width="100" />
            <el-table-column prop="warning_type" label="预警类型" width="100">
              <template #default="{ row }">
                <el-tag :type="getWarningType(row.warning_type)">{{ getWarningLabel(row.warning_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="次数" width="80">
              <template #default="{ row }">
                <span :class="getWarningClass(row.warning_type, row.count)">{{ row.count }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="details" label="详情" min-width="200" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="primary" link @click="showEmpDetail(row)">查看历史</el-button>
                <el-button v-if="row.warning_type === 'absent' || row.warning_type === 'late'" type="warning" link @click="openAdjustDialog(row)">签出培训</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="效能排名" name="ranking">
          <el-form inline>
            <el-form-item label="月份">
              <el-date-picker v-model="searchRank.year_month" type="month" value-format="YYYY-MM" />
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="searchRank.dept" placeholder="全部部门" clearable>
                <el-option v-for="d in depts" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadRanking">查询</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" v-if="rankingData.length" style="margin-bottom: 20px">
            <el-col :span="24">
              <el-card shadow="hover">
                <Echart :options="rankingChartOptions" :height="300" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="rankingData" border stripe>
            <el-table-column type="index" label="排名" width="60" />
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="100" />
            <el-table-column prop="dept" label="部门" width="100" />
            <el-table-column prop="efficiency_rate" label="效能得分" width="100" sortable>
              <template #default="{ row }">
                <span :class="getRateClass(row.efficiency_rate)">{{ row.efficiency_rate }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="attendance_rate" label="出勤率" width="90" sortable>
              <template #default="{ row }">
                {{ row.attendance_rate }}%
              </template>
            </el-table-column>
            <el-table-column prop="work_hours" label="工时得分" width="90" sortable>
              <template #default="{ row }">
                {{ row.work_hours }}
              </template>
            </el-table-column>
            <el-table-column prop="late_days" label="迟到" width="60" sortable>
              <template #default="{ row }">
                <span :class="{'text-warning': row.late_days > 0}">{{ row.late_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="absent_days" label="缺勤" width="60" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.absent_days > 0}">{{ row.absent_days }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="趋势分析" name="trend">
          <el-form inline>
            <el-form-item label="时间范围">
              <el-date-picker v-model="searchTrend.start_month" type="month" value-format="YYYY-MM" placeholder="开始月份" />
            </el-form-item>
            <el-form-item label="至">
              <el-date-picker v-model="searchTrend.end_month" type="month" value-format="YYYY-MM" placeholder="结束月份" />
            </el-form-item>
            <el-form-item label="员工">
              <el-select v-model="searchTrend.emp_no" placeholder="选择员工" filterable clearable>
                <el-option v-for="e in empList" :key="e.emp_no" :label="`${e.emp_no} - ${e.name}`" :value="e.emp_no" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadTrend">查询</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" v-if="trendData.length" style="margin-bottom: 20px">
            <el-col :span="24">
              <el-card shadow="hover">
                <Echart :options="trendChartOptions" :height="350" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="trendData" border stripe v-if="trendData.length">
            <el-table-column prop="year_month" label="月份" width="100" />
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="attendance_rate" label="出勤率" width="90">
              <template #default="{ row }">
                <span :class="getRateClass(row.attendance_rate)">{{ row.attendance_rate }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="efficiency_rate" label="工时效率" width="90">
              <template #default="{ row }">
                <span :class="getRateClass(row.efficiency_rate)">{{ row.efficiency_rate }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="scheduled_hours" label="计划工时" width="80" />
            <el-table-column prop="actual_hours" label="实际工时" width="80" />
            <el-table-column prop="late_days" label="迟到" width="60" />
            <el-table-column prop="absent_days" label="缺勤" width="60" />
            <el-table-column prop="work_days" label="出勤天数" width="80" />
          </el-table>
          <el-empty v-else description="请选择员工查询趋势数据" />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="detailDialogVisible" :title="`${detailData.name} - 效能详情`" width="900px">
      <el-descriptions :column="3" border v-if="detailData.emp_no">
        <el-descriptions-item label="工号">{{ detailData.emp_no }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ detailData.name }}</el-descriptions-item>
        <el-descriptions-item label="班组">{{ detailData.team }}</el-descriptions-item>
        <el-descriptions-item label="出勤率">{{ detailData.attendance_rate }}%</el-descriptions-item>
        <el-descriptions-item label="工时效率">{{ detailData.efficiency_rate }}%</el-descriptions-item>
        <el-descriptions-item label="出勤天数">{{ detailData.work_days }}天</el-descriptions-item>
      </el-descriptions>

      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <div style="margin-bottom: 10px; text-align: center; font-size: 14px; color: #606266">工时趋势</div>
          <Echart :options="detailHoursOptions" :height="250" />
        </el-col>
        <el-col :span="12">
          <div style="margin-bottom: 10px; text-align: center; font-size: 14px; color: #606266">考勤状态</div>
          <Echart :options="detailStatusOptions" :height="250" />
        </el-col>
      </el-row>

      <el-table :data="detailRecords" border stripe style="margin-top: 20px" max-height="300" :row-class-name="detailSegmentRowClass">
        <el-table-column prop="schedule_date" label="日期" width="120" />
        <el-table-column label="时段" width="60">
          <template #default="{ row }">
            <el-tag v-if="row._totalSegments > 1" size="small" type="info">{{ row._segLabel }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row._displayStatus || row.status)">{{ row._displayStatus || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="计划时间" width="150">
          <template #default="{ row }">
            {{ row._displayScheduledStart || row.scheduled_start }} - {{ row._displayScheduledEnd || row.scheduled_end }}
          </template>
        </el-table-column>
        <el-table-column label="实际签到" width="160">
          <template #default="{ row }">
            {{ row._displayCheckin || row.actual_checkin?.slice(0, 19) || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="迟到(分)" width="80">
          <template #default="{ row }">
            {{ row._displayLate ?? row.late_minutes }}
          </template>
        </el-table-column>
        <el-table-column label="计划工时" width="80">
          <template #default="{ row }">
            {{ row.scheduled_hours }}
          </template>
        </el-table-column>
        <el-table-column label="实际工时" width="80">
          <template #default="{ row }">
            {{ row._displayActualHours ?? row.actual_hours }}
          </template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班" width="60" />
      </el-table>
    </el-dialog>

    <el-dialog v-model="adjustDialogVisible" title="签出培训" width="500px">
      <el-form :model="adjustForm" label-width="80px">
        <el-form-item label="员工">
          <el-input v-model="adjustForm.name" disabled />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="adjustForm.dates" type="dates" value-format="YYYY-MM-DD" multiple placeholder="选择缺勤日期" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="adjustForm.type" placeholder="选择类型">
            <el-option label="签出培训" value="培训" />
            <el-option label="休息" value="休息" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="adjustForm.reason" type="textarea" placeholder="请输入原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdjust">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'
import Echart from '../components/Echart.vue'
import { createLineOptions, createBarOptions, createPieOptions, createHorizontalBarOptions } from '../utils/echarts'
import { usePersistedFilters } from '../composables/usePersistedFilters'

const savedTab = sessionStorage.getItem('efficiency-active-tab')
const activeTab = ref(savedTab || 'employee')
watch(activeTab, (val) => {
  sessionStorage.setItem('efficiency-active-tab', val)
})
const teams = ref([])
const depts = ref([])
const empList = ref([])

const now = new Date()
const yearMonth = now.toISOString().slice(0, 7)
const sixMonthsAgo = new Date(now.getFullYear(), now.getMonth() - 5, 1).toISOString().slice(0, 7)

const { filters: searchEmp } = usePersistedFilters('efficiency-emp', { year_month: yearMonth, dept: '', team: '' })
const { filters: searchWarn } = usePersistedFilters('efficiency-warn', { type: '', year_month: yearMonth })
const { filters: searchRank } = usePersistedFilters('efficiency-rank', { year_month: yearMonth, dept: '' })
const { filters: searchTrend } = usePersistedFilters('efficiency-trend', { start_month: sixMonthsAgo, end_month: yearMonth, emp_no: '' })

const empStats = reactive({ total: 0, avgAttendance: 0, avgEfficiency: 0, lateCount: 0, absentCount: 0, overtimeCount: 0 })
const empData = ref([])
const warningData = ref([])
const rankingData = ref([])
const trendData = ref([])

const detailDialogVisible = ref(false)
const detailData = ref({})
const detailRecords = ref([])

const adjustDialogVisible = ref(false)
const adjustForm = reactive({ emp_no: '', name: '', dates: [], type: '培训', reason: '' })

const empEfficiencyOptions = computed(() => {
  if (!empData.value.length) return {}
  const data = empData.value.slice(0, 10)
  return createBarOptions(data.map(d => d.name), data.map(d => d.efficiency_rate), '', '员工', '效率(%)')
})

const empAttendanceOptions = computed(() => {
  if (!empData.value.length) return {}
  const data = empData.value.slice(0, 10)
  return createBarOptions(data.map(d => d.name), data.map(d => d.attendance_rate), '', '员工', '出勤率(%)')
})

const rankingChartOptions = computed(() => {
  if (!rankingData.value.length) return {}
  const data = rankingData.value.slice(0, 10)
  return createHorizontalBarOptions(data.map(d => d.name), data.map(d => d.efficiency_rate), '', '员工', '效能得分')
})

const trendChartOptions = computed(() => {
  if (!trendData.value.length) return {}
  const months = trendData.value.map(d => d.year_month)
  const attendance = trendData.value.map(d => d.attendance_rate)
  const efficiency = trendData.value.map(d => d.efficiency_rate)
  return createLineOptions(months, [attendance, efficiency], '效能趋势', '月份', '百分比(%)')
})

const detailHoursOptions = computed(() => {
  if (!detailRecords.value.length) return {}
  const data = detailRecords.value.slice(-15)
  const dates = data.map(d => d.schedule_date.slice(5))
  const scheduled = data.map(d => d.scheduled_hours || 0)
  const actual = data.map(d => d.actual_hours || 0)
  return createBarOptions(dates, [scheduled, actual], '工时对比', '日期', '工时')
})

const detailStatusOptions = computed(() => {
  if (!detailRecords.value.length) return {}
  const statusCount = { '正常': 0, '迟到': 0, '早退': 0, '缺勤': 0, '请假': 0, '休息': 0 }
  detailRecords.value.forEach(d => { if (statusCount[d.status] !== undefined) statusCount[d.status]++ })
  const data = Object.entries(statusCount).filter(([, v]) => v > 0).map(([n, v]) => ({ name: n, value: v }))
  return createPieOptions(data, '考勤状态分布')
})

function getRateClass(rate) {
  if (rate >= 95) return 'text-success'
  if (rate >= 80) return ''
  if (rate >= 60) return 'text-warning'
  return 'text-danger'
}

function getStatusType(status) {
  const map = { '正常': 'success', '迟到': 'warning', '早退': 'warning', '缺勤': 'danger', '请假': 'info', '休息': '' }
  return map[status] || 'info'
}

function getWarningType(type) {
  const map = { 'late': 'warning', 'absent': 'danger', 'efficiency': 'danger' }
  return map[type] || 'info'
}

function getWarningLabel(type) {
  const map = { 'late': '迟到预警', 'absent': '缺勤预警', 'efficiency': '效率预警' }
  return map[type] || type
}

function getWarningClass(type, count) {
  if (type === 'late') return count >= 3 ? 'text-danger' : count >= 1 ? 'text-warning' : ''
  if (type === 'absent') return count >= 2 ? 'text-danger' : count >= 1 ? 'text-warning' : ''
  if (type === 'efficiency') return count < 80 ? 'text-danger' : ''
  return ''
}

async function loadFilters() {
  try {
    const [tRes, dRes, eRes] = await Promise.all([
      api.get('/employees/teams'),
      api.get('/employees/departments'),
      api.get('/employees', { params: { limit: 500 } })
    ])
    teams.value = tRes.data || []
    depts.value = dRes.data || []
    empList.value = eRes.data.items || []
  } catch (e) {
    console.error(e)
  }
}

async function loadEmployeeEfficiency() {
  if (!searchEmp.year_month) {
    searchEmp.year_month = new Date().toISOString().slice(0, 7)
  }
  try {
    const res = await api.get('/reports/employee-efficiency', { params: searchEmp })
    empData.value = res.data.items || []
    calcEmpStats(empData.value)
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

function calcEmpStats(data) {
  empStats.total = data.length
  if (!data.length) {
    empStats.avgAttendance = 0
    empStats.avgEfficiency = 0
    empStats.lateCount = 0
    empStats.absentCount = 0
    empStats.overtimeCount = 0
    return
  }
  const sum = data.reduce((s, d) => {
    s.attendance += d.attendance_rate || 0
    s.efficiency += d.efficiency_rate || 0
    s.late += d.late_days || 0
    s.absent += d.absent_days || 0
    s.overtime += d.overtime_hours > 0 ? 1 : 0
    return s
  }, { attendance: 0, efficiency: 0, late: 0, absent: 0, overtime: 0 })
  empStats.avgAttendance = Math.round(sum.attendance / data.length)
  empStats.avgEfficiency = Math.round(sum.efficiency / data.length)
  empStats.lateCount = data.filter(d => d.late_days > 0).length
  empStats.absentCount = data.filter(d => d.absent_days > 0).length
  empStats.overtimeCount = sum.overtime
}

async function loadWarnings() {
  if (!searchWarn.year_month) {
    searchWarn.year_month = new Date().toISOString().slice(0, 7)
  }
  try {
    const res = await api.get('/reports/efficiency-warning', { params: searchWarn })
    warningData.value = res.data || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadRanking() {
  if (!searchRank.year_month) {
    searchRank.year_month = new Date().toISOString().slice(0, 7)
  }
  try {
    const res = await api.get('/reports/employee-ranking', { params: searchRank })
    rankingData.value = res.data || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadTrend() {
  if (!searchTrend.start_month || !searchTrend.end_month || !searchTrend.emp_no) {
    ElMessage.warning('请选择时间范围和员工')
    return
  }
  try {
    const res = await api.get('/reports/emp-trend', { params: searchTrend })
    trendData.value = res.data || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function showEmpDetail(row) {
  detailData.value = row
  const params = {
    emp_no: row.emp_no,
    start_date: `${searchEmp.year_month || searchWarn.year_month || searchRank.year_month}-01`,
    end_date: `${searchEmp.year_month || searchWarn.year_month || searchRank.year_month}-31`
  }
  try {
    const res = await api.get('/reports/daily', { params })
    const items = res.data.items || []
    const expanded = []
    for (const item of items) {
      const segs = item.segment_details || []
      if (segs.length <= 1) {
        expanded.push({ ...item, _totalSegments: 1, _segLabel: '', _displayScheduledStart: null, _displayScheduledEnd: null, _displayCheckin: null, _displayLate: null, _displayActualHours: null, _displayStatus: null })
      } else {
        segs.forEach((seg, i) => {
          expanded.push({
            ...item,
            _totalSegments: segs.length,
            _segLabel: `${i + 1}/${segs.length}`,
            _displayScheduledStart: seg.start,
            _displayScheduledEnd: seg.end,
            _displayCheckin: seg.actual_checkin ? seg.actual_checkin.slice(0, 19) : '-',
            _displayLate: seg.late_minutes,
            _displayActualHours: seg.actual_hours,
            _displayStatus: seg.status
          })
        })
      }
    }
    detailRecords.value = expanded
    detailDialogVisible.value = true
  } catch (e) {
    detailRecords.value = []
    detailDialogVisible.value = true
  }
}

function detailSegmentRowClass({ row }) {
  return row._totalSegments > 1 ? 'segment-sub-row' : ''
}

function openAdjustDialog(row) {
  adjustForm.emp_no = row.emp_no
  adjustForm.name = row.name
  adjustForm.dates = []
  adjustForm.type = '培训'
  adjustForm.reason = ''
  adjustDialogVisible.value = true
}

async function handleAdjust() {
  if (!adjustForm.dates.length || !adjustForm.type) {
    ElMessage.warning('请选择日期和类型')
    return
  }
  try {
    await api.post('/reports/adjust-status', {
      emp_no: adjustForm.emp_no,
      dates: adjustForm.dates,
      status: adjustForm.type,
      reason: adjustForm.reason
    })
    ElMessage.success('签出培训设置成功')
    adjustDialogVisible.value = false
    loadWarnings()
    loadEmployeeEfficiency()
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  loadFilters()
  loadEmployeeEfficiency()
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.text-success { color: #67c23a; font-weight: bold; }
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; font-weight: bold; }
</style>