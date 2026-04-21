<template>
  <div class="reports">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>考勤报表</span>
          <el-button type="primary" @click="handleExport">导出</el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="日报表" name="daily">
          <el-form inline>
            <el-form-item label="日期">
              <el-date-picker v-model="searchDaily.date" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchDaily.team" placeholder="请选择" clearable>
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="searchDaily.status" placeholder="请选择" clearable>
                <el-option label="正常" value="正常" />
                <el-option label="迟到" value="迟到" />
                <el-option label="早退" value="早退" />
                <el-option label="缺勤" value="缺勤" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadDaily">查询</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="dailyData" border stripe>
            <el-table-column prop="schedule_date" label="日期" width="120" />
            <el-table-column prop="emp_id" label="员工ID" width="80" />
            <el-table-column prop="schedule_type" label="排班类型" width="100" />
            <el-table-column prop="scheduled_start" label="计划开始" width="100" />
            <el-table-column prop="scheduled_end" label="计划结束" width="100" />
            <el-table-column prop="actual_checkin" label="实际签到" width="180">
              <template #default="{ row }">
                {{ row.actual_checkin?.slice(0, 19) }}
              </template>
            </el-table-column>
            <el-table-column prop="actual_checkout" label="实际签退" width="180">
              <template #default="{ row }">
                {{ row.actual_checkout?.slice(0, 19) }}
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
              <el-date-picker v-model="searchMonthly.year_month" type="month" value-format="YYYY-MM" />
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchMonthly.team" placeholder="请选择" clearable>
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadMonthly">查询</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="monthlyData" border stripe>
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="120" />
            <el-table-column prop="dept" label="部门" width="120" />
            <el-table-column prop="scheduled_hours" label="计划工时" width="100" />
            <el-table-column prop="actual_hours" label="实际工时" width="100" />
            <el-table-column prop="overtime_hours" label="加班工时" width="100" />
            <el-table-column prop="owed_hours" label="欠时工时" width="100" />
            <el-table-column prop="normal_days" label="正常" width="60" />
            <el-table-column prop="late_days" label="迟到" width="60" />
            <el-table-column prop="early_days" label="早退" width="60" />
            <el-table-column prop="absent_days" label="缺勤" width="60" />
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
            <el-form-item label="班组">
              <el-select v-model="searchRange.team" placeholder="请选择" clearable>
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="searchRange.status" placeholder="请选择" clearable>
                <el-option label="正常" value="正常" />
                <el-option label="迟到" value="迟到" />
                <el-option label="早退" value="早退" />
                <el-option label="缺勤" value="缺勤" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadRange">查询</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="rangeData" border stripe>
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="120" />
            <el-table-column prop="dept" label="部门" width="120" />
            <el-table-column prop="scheduled_hours" label="计划工时" width="100" />
            <el-table-column prop="actual_hours" label="实际工时" width="100" />
            <el-table-column prop="overtime_hours" label="加班工时" width="100" />
            <el-table-column prop="owed_hours" label="欠时工时" width="100" />
            <el-table-column prop="normal_days" label="正常" width="60" />
            <el-table-column prop="late_days" label="迟到" width="60" />
            <el-table-column prop="early_days" label="早退" width="60" />
            <el-table-column prop="absent_days" label="缺勤" width="60" />
            <el-table-column prop="leave_days" label="请假" width="60" />
            <el-table-column prop="timeoff_days" label="公休" width="60" />
            <el-table-column prop="work_days" label="出勤天数" width="80" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'

const activeTab = ref('daily')
const dailyData = ref([])
const monthlyData = ref([])
const rangeData = ref([])
const teams = ref([])
const searchDaily = reactive({ date: '', team: '', status: '' })
const searchMonthly = reactive({ year_month: '', team: '' })
const searchRange = reactive({ start_date: '', end_date: '', team: '', status: '' })

function getStatusType(status) {
  const map = { '正常': 'success', '迟到': 'warning', '早退': 'warning', '缺勤': 'danger' }
  return map[status] || 'info'
}

async function loadDaily() {
  try {
    const res = await api.get('/reports/daily', { params: searchDaily })
    dailyData.value = res.data.items
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

async function loadMonthly() {
  try {
    const res = await api.get('/reports/month-summary', { params: searchMonthly })
    monthlyData.value = res.data
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

async function loadRange() {
  if (!searchRange.start_date || !searchRange.end_date) {
    ElMessage.warning('请选择开始和结束日期')
    return
  }
  try {
    const res = await api.get('/reports/date-range', { params: searchRange })
    rangeData.value = res.data.items
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

async function loadTeams() {
  try {
    const res = await api.get('/employees/teams')
    teams.value = res.data
  } catch (e) {
    console.error(e)
  }
}

function handleExport() {
  ElMessage.info('导出功能开发中')
}

onMounted(() => {
  loadTeams()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>