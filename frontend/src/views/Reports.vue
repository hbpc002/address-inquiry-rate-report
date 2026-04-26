<template>
  <div class="reports">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>考勤报表</span>
          <el-space>
            <el-button type="success" @click="handleExport">导出报表</el-button>
          </el-space>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="日报表" name="daily">
          <el-form inline>
            <el-form-item label="日期">
              <el-date-picker v-model="searchDaily.schedule_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="searchDaily.dept" placeholder="全部部门" clearable filterable>
                <el-option v-for="d in depts" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchDaily.team" placeholder="全部班组" clearable filterable>
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="searchDaily.status" placeholder="全部状态" clearable>
                <el-option label="正常" value="正常" />
                <el-option label="迟到" value="迟到" />
                <el-option label="早退" value="早退" />
                <el-option label="缺勤" value="缺勤" />
                <el-option label="请假" value="请假" />
                <el-option label="公休" value="公休" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadDaily">查询</el-button>
              <el-button @click="resetDaily">重置</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" class="stats-row">
            <el-col :span="4">
              <el-statistic title="应到人数" :value="dailyStats.total" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="出勤人数" :value="dailyStats.attend" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="正常" :value="dailyStats.normal" >
                <template #suffix><span class="stat-normal">人</span></template>
              </el-statistic>
            </el-col>
            <el-col :span="4">
              <el-statistic title="迟到" :value="dailyStats.late" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="缺勤" :value="dailyStats.absent" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="出勤率" :value="dailyStats.rate" :precision="1" suffix="%" />
            </el-col>
          </el-row>

          <el-row :gutter="20" v-if="dailyData.length" style="margin-bottom: 20px">
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="dailyChartOptions" :height="280" @click="handleDailyChartClick" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <div style="margin-bottom: 10px; text-align: center; font-size: 14px; color: #606266">部门出勤对比</div>
                <Echart :options="monthlyDeptOptions" :height="250" @click="handleDeptChartClick" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="dailyData" border stripe show-summary>
            <el-table-column prop="schedule_date" label="日期" width="120" />
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="100" />
            <el-table-column prop="dept" label="部门" width="120" />
            <el-table-column prop="schedule_type" label="排班类型" width="80" />
            <el-table-column prop="scheduled_start" label="计划开始" width="80" />
            <el-table-column prop="scheduled_end" label="计划结束" width="80" />
            <el-table-column prop="actual_checkin" label="实际签到" width="160">
              <template #default="{ row }">
                <span :class="{'text-warning': row.late_minutes > 0}">
                  {{ row.actual_checkin?.slice(0, 19) || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="actual_checkout" label="实际签退" width="160">
              <template #default="{ row }">
                <span :class="{'text-warning': row.early_minutes > 0}">
                  {{ row.actual_checkout?.slice(0, 19) || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="late_minutes" label="迟到(分)" width="80" />
            <el-table-column prop="early_minutes" label="早退(分)" width="80" />
            <el-table-column prop="actual_hours" label="实际工时" width="80" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="月度汇总" name="month">
          <el-form inline>
            <el-form-item label="月份">
              <el-date-picker v-model="searchMonthly.year_month" type="month" value-format="YYYY-MM" placeholder="选择月份" />
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="searchMonthly.dept" placeholder="全部部门" clearable filterable>
                <el-option v-for="d in depts" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchMonthly.team" placeholder="全部班组" clearable filterable>
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadMonthly">查询</el-button>
              <el-button @click="resetMonthly">重置</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" class="stats-row">
            <el-col :span="4">
              <el-statistic title="员工人数" :value="monthlyStats.total" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="计划工时" :value="monthlyStats.scheduled" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="实际工时" :value="monthlyStats.actual" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="加班工时" :value="monthlyStats.overtime" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="欠时工时" :value="monthlyStats.owed" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="出勤天数" :value="monthlyStats.workDays" :precision="0" />
            </el-col>
          </el-row>

          <el-row :gutter="20" v-if="monthlyData.length" style="margin-bottom: 20px">
            <el-col :span="12">
              <el-card shadow="hover">
                <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center">
                  <span style="font-size: 14px; color: #606266">部门工时对比</span>
                  <el-radio-group v-model="currentChartType" size="small">
                    <el-radio-button value="bar">柱状图</el-radio-button>
                    <el-radio-button value="line">折线图</el-radio-button>
                  </el-radio-group>
                </div>
                <Echart :options="monthlyDeptOptions" :height="250" @click="handleDeptChartClick" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="monthlyOvertimeOptions" :height="280" @click="handleOvertimeChartClick" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="monthlyData" border stripe show-summary>
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="100" />
            <el-table-column prop="dept" label="部门" width="120" />
            <el-table-column prop="scheduled_hours" label="计划工时" width="90" sortable />
            <el-table-column prop="actual_hours" label="实际工时" width="90" sortable />
            <el-table-column prop="overtime_hours" label="加班" width="70" sortable>
              <template #default="{ row }">
                <span :class="{'text-success': row.overtime_hours > 0}">{{ row.overtime_hours }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="owed_hours" label="欠时" width="70" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.owed_hours > 0}">{{ row.owed_hours }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="normal_days" label="正常" width="60" sortable />
            <el-table-column prop="late_days" label="迟到" width="60" sortable>
              <template #default="{ row }">
                <span :class="{'text-warning': row.late_days > 0}">{{ row.late_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="early_days" label="早退" width="60" sortable />
            <el-table-column prop="absent_days" label="缺勤" width="60" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.absent_days > 0}">{{ row.absent_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="leave_days" label="请假" width="60" />
            <el-table-column prop="timeoff_days" label="公休" width="60" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="自定义时间段" name="daterange">
          <el-form inline>
            <el-form-item label="开始日期">
              <el-date-picker v-model="searchRange.start_date" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker v-model="searchRange.end_date" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="searchRange.dept" placeholder="全部部门" clearable filterable>
                <el-option v-for="d in depts" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchRange.team" placeholder="全部班组" clearable filterable>
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="searchRange.status" placeholder="全部状态" clearable>
                <el-option label="正常" value="正常" />
                <el-option label="迟到" value="迟到" />
                <el-option label="早退" value="早退" />
                <el-option label="缺勤" value="缺勤" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadRange">查询</el-button>
              <el-button @click="resetRange">重置</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" class="stats-row">
            <el-col :span="4">
              <el-statistic title="员工人数" :value="rangeStats.total" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总计划工时" :value="rangeStats.scheduled" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总实际工时" :value="rangeStats.actual" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总加班" :value="rangeStats.overtime" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总欠时" :value="rangeStats.owed" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总出勤天数" :value="rangeStats.workDays" :precision="0" />
            </el-col>
          </el-row>

          <el-row :gutter="20" v-if="rangeData.length" style="margin-bottom: 20px">
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="rangeDeptOptions" :height="280" @click="handleDeptChartClick" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="rangeStatusOptions" :height="280" @click="handleRangeStatusClick" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="rangeData" border stripe show-summary>
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="100" />
            <el-table-column prop="dept" label="部门" width="120" />
            <el-table-column prop="scheduled_hours" label="计划工时" width="90" sortable />
            <el-table-column prop="actual_hours" label="实际工时" width="90" sortable />
            <el-table-column prop="overtime_hours" label="加班" width="70" sortable>
              <template #default="{ row }">
                <span :class="{'text-success': row.overtime_hours > 0}">{{ row.overtime_hours }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="owed_hours" label="欠时" width="70" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.owed_hours > 0}">{{ row.owed_hours }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="normal_days" label="正常" width="60" sortable />
            <el-table-column prop="late_days" label="迟到" width="60" sortable>
              <template #default="{ row }">
                <span :class="{'text-warning': row.late_days > 0}">{{ row.late_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="early_days" label="早退" width="60" sortable />
            <el-table-column prop="absent_days" label="缺勤" width="60" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.absent_days > 0}">{{ row.absent_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="leave_days" label="请假" width="60" />
            <el-table-column prop="timeoff_days" label="公休" width="60" />
            <el-table-column prop="work_days" label="出勤天数" width="80" sortable />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="班组排名" name="ranking">
          <el-form inline>
            <el-form-item label="月份">
              <el-date-picker v-model="searchRank.year_month" type="month" value-format="YYYY-MM" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadRanking">查询</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" v-if="rankingData.length" style="margin-bottom: 20px">
            <el-col :span="24">
              <el-card shadow="hover">
                <Echart :options="rankingChartOptions" :height="300" @click="handleRankingChartClick" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="rankingData" border stripe>
            <el-table-column type="index" label="排名" width="60" />
            <el-table-column prop="team" label="班组" width="150" />
            <el-table-column prop="emp_count" label="人数" width="80" sortable />
            <el-table-column prop="total_scheduled" label="计划工时" width="100" sortable />
            <el-table-column prop="total_actual" label="实际工时" width="100" sortable />
            <el-table-column prop="total_overtime" label="加班工时" width="100" sortable />
            <el-table-column prop="avg_attendance" label="平均出勤率" width="110" sortable>
              <template #default="{ row }">
                {{ (row.avg_attendance * 100).toFixed(1) }}%
              </template>
            </el-table-column>
            <el-table-column prop="late_count" label="迟到次数" width="90" sortable />
            <el-table-column prop="absent_count" label="缺勤次数" width="90" sortable />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="exportDialogVisible" title="导出报表" width="400px">
      <el-form :model="exportForm" label-width="80px">
        <el-form-item label="报表类型">
          <el-select v-model="exportForm.type">
            <el-option label="日报表" value="daily" />
            <el-option label="月报表" value="month" />
            <el-option label="时间段" value="date_range" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="exportForm.type === 'daily'" label="日期">
          <el-date-picker v-model="exportForm.schedule_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item v-if="exportForm.type === 'month'" label="月份">
          <el-date-picker v-model="exportForm.year_month" type="month" value-format="YYYY-MM" />
        </el-form-item>
        <el-form-item v-if="exportForm.type === 'date_range'" label="日期范围">
          <el-date-picker v-model="exportForm.dateRange" type="daterange" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="exportForm.team" clearable placeholder="全部">
            <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmExport">确定导出</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialogVisible" :title="detailTitle" width="800px">
      <el-table :data="detailData" border stripe max-height="400" v-if="detailData.length">
        <el-table-column prop="emp_no" label="工号" width="100" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="team" label="班组" width="120" />
        <el-table-column prop="dept" label="部门" width="120" />
        <el-table-column prop="schedule_date" label="日期" width="120" v-if="activeTab === 'daily' || activeTab === 'daterange'" />
        <el-table-column prop="status" label="状态" width="80" v-if="activeTab !== 'month'">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actual_hours" label="实际工时" width="90" v-if="activeTab === 'month' || activeTab === 'daterange'" />
        <el-table-column prop="overtime_hours" label="加班" width="70" v-if="activeTab === 'month' || activeTab === 'daterange'">
          <template #default="{ row }">
            <span :class="{'text-success': row.overtime_hours > 0}">{{ row.overtime_hours }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="owed_hours" label="欠时" width="70" v-if="activeTab === 'month' || activeTab === 'daterange'">
          <template #default="{ row }">
            <span :class="{'text-danger': row.owed_hours > 0}">{{ row.owed_hours }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!detailData.length" description="暂无数据" />
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'
import Echart from '../components/Echart.vue'
import { createPieOptions, createBarOptions, createLineOptions, createHorizontalBarOptions, createMultiBarOptions } from '../utils/echarts'

const activeTab = ref('daily')
const dailyData = ref([])
const monthlyData = ref([])
const rangeData = ref([])
const rankingData = ref([])
const teams = ref([])
const depts = ref([])

const dailyStats = reactive({ total: 0, attend: 0, normal: 0, late: 0, absent: 0, rate: 0 })
const monthlyStats = reactive({ total: 0, scheduled: 0, actual: 0, overtime: 0, owed: 0, workDays: 0 })
const rangeStats = reactive({ total: 0, scheduled: 0, actual: 0, overtime: 0, owed: 0, workDays: 0 })

const searchDaily = reactive({ schedule_date: '', dept: '', team: '', status: '' })
const searchMonthly = reactive({ year_month: '', dept: '', team: '' })
const searchRange = reactive({ start_date: '', end_date: '', dept: '', team: '', status: '' })
const searchRank = reactive({ year_month: '' })

const exportDialogVisible = ref(false)
const exportForm = reactive({ type: 'month', schedule_date: '', year_month: '', dateRange: [], team: '' })

const currentChartType = ref('bar')
const detailDialogVisible = ref(false)
const detailTitle = ref('')
const detailData = ref([])

const dailyChartOptions = computed(() => {
  if (!dailyData.value.length) return {}
  const statusCount = {}
  dailyData.value.forEach(d => { statusCount[d.status] = (statusCount[d.status] || 0) + 1 })
  const pieData = Object.entries(statusCount).map(([name, value]) => ({ name, value }))
  return createPieOptions(pieData, '考勤状态分布')
})

const monthlyDeptOptions = computed(() => {
  if (!monthlyData.value.length) return {}
  const deptMap = {}
  monthlyData.value.forEach(d => {
    if (!deptMap[d.dept]) deptMap[d.dept] = { scheduled: 0, actual: 0 }
    deptMap[d.dept].scheduled += d.scheduled_hours || 0
    deptMap[d.dept].actual += d.actual_hours || 0
  })
  const depts = Object.keys(deptMap).slice(0, 8)
  if (currentChartType.value === 'line') {
    return createLineOptions(depts, depts.map(d => Math.round(deptMap[d].actual)), '部门工时趋势', '部门', '实际工时')
  }
  return createMultiBarOptions(depts, [
    { name: '计划工时', data: depts.map(d => Math.round(deptMap[d].scheduled)) },
    { name: '实际工时', data: depts.map(d => Math.round(deptMap[d].actual)) }
  ], '部门工时对比')
})

const monthlyOvertimeOptions = computed(() => {
  if (!monthlyData.value.length) return {}
  const overtime = monthlyData.value.filter(d => d.overtime_hours > 0).length
  const owed = monthlyData.value.filter(d => d.owed_hours > 0).length
  const normal = monthlyData.value.length - overtime - owed
  return createPieOptions([
    { name: '正常', value: normal },
    { name: '加班', value: overtime },
    { name: '欠时', value: owed }
  ], '加班/欠时分布', ['#67c23a', '#e6a23c', '#f56c6c'])
})

const rangeDeptOptions = computed(() => {
  if (!rangeData.value.length) return {}
  const deptMap = {}
  rangeData.value.forEach(d => {
    if (!deptMap[d.dept]) deptMap[d.dept] = { scheduled: 0, actual: 0 }
    deptMap[d.dept].scheduled += d.scheduled_hours || 0
    deptMap[d.dept].actual += d.actual_hours || 0
  })
  const depts = Object.keys(deptMap).slice(0, 8)
  if (currentChartType.value === 'line') {
    return createLineOptions(depts, depts.map(d => Math.round(deptMap[d].actual)), '部门工时趋势', '部门', '实际工时')
  }
  return createMultiBarOptions(depts, [
    { name: '计划工时', data: depts.map(d => Math.round(deptMap[d].scheduled)) },
    { name: '实际工时', data: depts.map(d => Math.round(deptMap[d].actual)) }
  ], '部门工时对比')
})

const rangeStatusOptions = computed(() => {
  if (!rangeData.value.length) return {}
  const statusCount = { '正常': 0, '迟到': 0, '早退': 0, '缺勤': 0, '请假': 0, '公休': 0 }
  rangeData.value.forEach(d => { if (statusCount[d.status] !== undefined) statusCount[d.status]++ })
  const data = Object.entries(statusCount).filter(([, v]) => v > 0).map(([n, v]) => ({ name: n, value: v }))
  return createPieOptions(data, '异常考勤分布')
})

const rankingChartOptions = computed(() => {
  if (!rankingData.value.length) return {}
  const data = [...rankingData.value].sort((a, b) => b.avg_attendance - a.avg_attendance).slice(0, 8)
  return createHorizontalBarOptions(data.map(d => d.team), data.map(d => Math.round(d.avg_attendance * 100)), '', '班组', '出勤率(%)')
})

function getStatusType(status) {
  const map = { '正常': 'success', '迟到': 'warning', '早退': 'warning', '缺勤': 'danger', '请假': 'info', '公休': '' }
  return map[status] || 'info'
}

function calcDailyStats(data) {
  dailyStats.total = data.length
  dailyStats.attend = data.filter(d => d.status !== '缺勤').length
  dailyStats.normal = data.filter(d => d.status === '正常').length
  dailyStats.late = data.filter(d => d.status === '迟到').length
  dailyStats.absent = data.filter(d => d.status === '缺勤').length
  dailyStats.rate = dailyStats.total ? Math.round(dailyStats.attend / dailyStats.total * 100) : 0
}

function calcMonthlyStats(data) {
  monthlyStats.total = data.length
  monthlyStats.scheduled = data.reduce((s, d) => s + (d.scheduled_hours || 0), 0)
  monthlyStats.actual = data.reduce((s, d) => s + (d.actual_hours || 0), 0)
  monthlyStats.overtime = data.reduce((s, d) => s + (d.overtime_hours || 0), 0)
  monthlyStats.owed = data.reduce((s, d) => s + (d.owed_hours || 0), 0)
  monthlyStats.workDays = data.reduce((s, d) => s + (d.normal_days || 0), 0)
}

function calcRangeStats(data) {
  rangeStats.total = data.length
  rangeStats.scheduled = data.reduce((s, d) => s + (d.scheduled_hours || 0), 0)
  rangeStats.actual = data.reduce((s, d) => s + (d.actual_hours || 0), 0)
  rangeStats.overtime = data.reduce((s, d) => s + (d.overtime_hours || 0), 0)
  rangeStats.owed = data.reduce((s, d) => s + (d.owed_hours || 0), 0)
  rangeStats.workDays = data.reduce((s, d) => s + (d.work_days || 0), 0)
}

async function loadDaily() {
  if (!searchDaily.date) {
    searchDaily.date = new Date().toISOString().slice(0, 10)
  }
  try {
    const res = await api.get('/reports/daily', { params: searchDaily })
    dailyData.value = res.data.items || []
    calcDailyStats(dailyData.value)
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadMonthly() {
  if (!searchMonthly.year_month) {
    searchMonthly.year_month = new Date().toISOString().slice(0, 7)
  }
  try {
    const res = await api.get('/reports/month-summary', { params: searchMonthly })
    monthlyData.value = res.data || []
    calcMonthlyStats(monthlyData.value)
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadRange() {
  if (!searchRange.start_date || !searchRange.end_date) {
    ElMessage.warning('请选择开始和结束日期')
    return
  }
  try {
    const res = await api.get('/reports/date-range', { params: searchRange })
    rangeData.value = res.data.items || []
    calcRangeStats(rangeData.value)
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadRanking() {
  if (!searchRank.year_month) {
    searchRank.year_month = new Date().toISOString().slice(0, 7)
  }
  try {
    const res = await api.get('/reports/team-ranking', { params: { year_month: searchRank.year_month } })
    rankingData.value = res.data || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
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

async function loadDepts() {
  try {
    const res = await api.get('/employees/departments')
    depts.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

function resetDaily() {
  searchDaily.schedule_date = new Date().toISOString().slice(0, 10)
  searchDaily.dept = ''
  searchDaily.team = ''
  searchDaily.status = ''
  loadDaily()
}

function resetMonthly() {
  searchMonthly.year_month = new Date().toISOString().slice(0, 7)
  searchMonthly.dept = ''
  searchMonthly.team = ''
  loadMonthly()
}

function resetRange() {
  const now = new Date()
  searchRange.start_date = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
  searchRange.end_date = now.toISOString().slice(0, 10)
  searchRange.dept = ''
  searchRange.team = ''
  searchRange.status = ''
  loadRange()
}

function handleExport() {
  exportForm.type = 'month'
  exportForm.year_month = new Date().toISOString().slice(0, 7)
  exportForm.team = ''
  exportDialogVisible.value = true
}

function confirmExport() {
  const params = new URLSearchParams()
  params.append('type', exportForm.type)
  if (exportForm.team) params.append('team', exportForm.team)

  if (exportForm.type === 'daily' && exportForm.schedule_date) {
    params.append('schedule_date', exportForm.schedule_date)
  } else if (exportForm.type === 'month' && exportForm.year_month) {
    params.append('year_month', exportForm.year_month)
  } else if (exportForm.type === 'date_range' && exportForm.dateRange?.length === 2) {
    params.append('start_date', exportForm.dateRange[0])
    params.append('end_date', exportForm.dateRange[1])
  }

  const url = `${import.meta.env.VITE_API_BASE_URL || '/api'}/reports/export?${params}`
  window.open(url, '_blank')
  exportDialogVisible.value = false
  ElMessage.success('导出成功')
}

function handleDailyChartClick(params) {
  const status = params.name
  const filtered = dailyData.value.filter(d => d.status === status)
  detailTitle.value = `${status}人员列表 (${filtered.length}人)`
  detailData.value = filtered
  detailDialogVisible.value = true
}

function handleDeptChartClick(params) {
  const deptName = params.name
  let data = []
  if (activeTab.value === 'month') {
    data = monthlyData.value.filter(d => d.dept === deptName)
  } else if (activeTab.value === 'daterange') {
    data = rangeData.value.filter(d => d.dept === deptName)
  } else if (activeTab.value === 'daily') {
    data = dailyData.value.filter(d => d.dept === deptName)
  }
  detailTitle.value = `${deptName}员工列表 (${data.length}人)`
  detailData.value = data
  detailDialogVisible.value = true
}

function handleOvertimeChartClick(params) {
  const type = params.name
  let data = []
  if (type === '加班') {
    data = monthlyData.value.filter(d => d.overtime_hours > 0)
  } else if (type === '欠时') {
    data = monthlyData.value.filter(d => d.owed_hours > 0)
  } else {
    data = monthlyData.value.filter(d => d.overtime_hours <= 0 && d.owed_hours <= 0)
  }
  detailTitle.value = `${type}人员列表 (${data.length}人)`
  detailData.value = data
  detailDialogVisible.value = true
}

function handleRangeStatusClick(params) {
  const status = params.name
  const filtered = rangeData.value.filter(d => d.status === status)
  detailTitle.value = `${status}人员列表 (${filtered.length}人)`
  detailData.value = filtered
  detailDialogVisible.value = true
}

function handleRankingChartClick(params) {
  const teamName = params.name
  const teamData = rankingData.value.find(r => r.team === teamName)
  if (teamData) {
    detailTitle.value = `${teamName} - 排名${rankingData.value.sort((a, b) => b.avg_attendance - a.avg_attendance).findIndex(r => r.team === teamName) + 1} (${teamData.emp_count}人, 出勤率${Math.round(teamData.avg_attendance * 100)}%)`
    detailData.value = []
  }
  detailDialogVisible.value = true
}

onMounted(() => {
  const today = new Date().toISOString().slice(0, 10)
  searchDaily.schedule_date = today
  searchMonthly.year_month = new Date().toISOString().slice(0, 7)
  searchRank.year_month = new Date().toISOString().slice(0, 7)
  
  const now = new Date()
  searchRange.start_date = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
  searchRange.end_date = now.toISOString().slice(0, 10)
  
  loadTeams()
  loadDepts()
  loadDaily()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-row {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.text-success { color: #67c23a; font-weight: bold; }
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; font-weight: bold; }

.stat-normal { color: #67c23a; }
</style>