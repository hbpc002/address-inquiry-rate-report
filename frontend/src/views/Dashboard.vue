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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../stores/user'

const stats = ref({
  employeeCount: 0,
  todayAttendance: 0,
  todayLate: 0,
  todayAbsent: 0
})

onMounted(async () => {
  try {
    const res = await api.get('/stats')
    stats.value = res.data
  } catch (e) {
    stats.value = { employeeCount: 0, todayAttendance: 0, todayLate: 0, todayAbsent: 0 }
  }
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