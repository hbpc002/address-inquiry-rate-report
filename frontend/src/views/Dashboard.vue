<template>
  <div class="dashboard">
    <el-card class="data-date-banner" :body-style="{ padding: '12px 20px' }">
      <div class="banner-content">
        <div class="date-info">
          <el-tag type="success" effect="dark">数据</el-tag>
          <span class="date-text">数据已更新至：<strong>{{ stats.latest_data_date || '暂无数据' }}</strong></span>
          <span class="report-count" v-if="stats.latest_attendance + stats.latest_leave + stats.latest_timeoff + stats.latest_absent > 0">
            （最新日出勤 {{ stats.latest_attendance }} / 请假 {{ stats.latest_leave }} / 休息 {{ stats.latest_timeoff }} / 缺勤 {{ stats.latest_absent }}）
          </span>
        </div>
        <div style="display:flex;align-items:center;gap:12px">
          <el-date-picker v-model="yearMonth" type="month" value-format="YYYY-MM" placeholder="选择月份" size="small" style="width:140px" @change="onMonthChange" />
          <div class="changelog-carousel" v-if="changelog.length > 0">
            <el-tag type="warning" effect="dark" size="small">更新日志</el-tag>
            <el-carousel height="32px" direction="vertical" :autoplay="true" indicator-position="none" class="carousel-inline">
              <el-carousel-item v-for="log in changelog" :key="log.id" class="carousel-item-content">
                <span class="carousel-text">{{ log.title }}：{{ log.content }}</span>
                <el-button type="warning" link size="small" @click="showChangelogDetail(log)">详情</el-button>
              </el-carousel-item>
            </el-carousel>
            <el-button type="warning" link size="small" @click="showAllChangelog">查看全部</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <el-row :gutter="12" style="margin-top:20px">
      <el-col :span="12">
        <el-card><template #header><span>工时完成趋势</span></template>
          <Echart :options="hoursTrendOptions" :height="320" @click="handleTrendClick" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card><template #header><span>工时分布</span></template>
          <Echart :options="hoursDistOptions" :height="320" @click="handleDistClick" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="12" style="margin-top:20px">
      <el-col :span="12">
        <el-card><template #header><span>每日产量趋势</span></template>
          <ChartPanel fullscreenable>
            <Echart :options="dailyProdOptions" :height="320" @click="handleDailyProdClick" />
          </ChartPanel>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card><template #header><span>班组综合对比</span></template>
          <ChartPanel fullscreenable>
            <Echart :options="mergedTeamOptions" :height="320" />
          </ChartPanel>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="trendDetailVisible" :title="'工时明细 - ' + trendDetailDate" width="900px">
      <el-table :data="trendDetailData" border stripe max-height="500">
        <el-table-column prop="emp_no" label="工号" width="100" />
        <el-table-column prop="name" label="姓名" width="90" />
        <el-table-column prop="team" label="班组" width="100" />
        <el-table-column prop="status" label="状态" width="70">
          <template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="scheduled_hours" label="应出勤" width="80" />
        <el-table-column prop="actual_hours" label="实际" width="80" />
        <el-table-column prop="overtime_hours" label="加班" width="80" />
        <el-table-column prop="late_minutes" label="迟到(分)" width="80" />
        <el-table-column prop="early_minutes" label="早退(分)" width="80" />
      </el-table>
      <template #footer><el-button @click="trendDetailVisible = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="distDetailVisible" :title="distDetailTitle" width="800px">
      <el-table :data="distDetailData" border stripe max-height="500">
        <el-table-column prop="emp_no" label="工号" width="100" />
        <el-table-column prop="name" label="姓名" width="90" />
        <el-table-column prop="team" label="班组" width="100" />
        <el-table-column prop="actual_hours" label="实际工时" width="90" />
        <el-table-column prop="status" label="状态" width="70">
          <template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
      </el-table>
      <template #footer><el-button @click="distDetailVisible = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="allChangelogVisible" title="全部更新日志" width="800px">
      <el-table :data="allChangelogs" border stripe max-height="500">
        <el-table-column prop="title" label="标题" width="140" />
        <el-table-column prop="content" label="内容" min-width="300" />
        <el-table-column prop="created_at" label="时间" width="120"><template #default="{ row }">{{ (row.created_at || '').slice(0, 10) }}</template></el-table-column>
        <el-table-column label="操作" width="70"><template #default="{ row }"><el-button type="warning" link size="small" @click="showChangelogDetail(row)">详情</el-button></template></el-table-column>
      </el-table>
      <template #footer><el-button @click="allChangelogVisible = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="changelogDetailVisible" title="更新日志详情" width="600px">
      <div v-if="currentChangelog">
        <h3>{{ currentChangelog.title }}</h3>
        <p style="white-space:pre-wrap;line-height:1.8;margin-top:12px">{{ currentChangelog.content }}</p>
        <el-text type="info" size="small" style="margin-top:16px;display:block">{{ (currentChangelog.created_at || '').slice(0, 10) }}</el-text>
      </div>
      <template #footer><el-button @click="changelogDetailVisible = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="dailyProdDetailVisible" :title="'产量明细 - ' + dailyProdDetailDate" width="800px">
      <el-table :data="dailyProdDetailData" border stripe max-height="500" v-if="dailyProdDetailData.length">
        <el-table-column prop="account" label="账号" width="110" />
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column prop="team_desc" label="班组" min-width="140" />
        <el-table-column prop="call_count" label="通话量" width="80" sortable />
        <el-table-column prop="ticket_count" label="工单量" width="80" sortable />
        <el-table-column prop="outbound_count" label="呼出量" width="80" sortable />
      </el-table>
      <div v-else style="text-align:center;padding:40px;color:#999">该日无产量数据</div>
      <template #footer><el-button @click="dailyProdDetailVisible = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../stores/user'
import Echart from '../components/Echart.vue'
import ChartPanel from '../components/ChartPanel.vue'


const stats = ref({
  employee_count: 0, latest_data_date: null,
  latest_attendance: 0, latest_late: 0, latest_absent: 0, latest_leave: 0, latest_timeoff: 0,
  monthly_total_days: 0, monthly_normal_days: 0, monthly_late_days: 0,
  monthly_absent_days: 0, monthly_leave_days: 0, monthly_timeoff_days: 0,
  monthly_actual_hours: 0, monthly_scheduled_hours: 0, monthly_overtime_hours: 0, monthly_owed_hours: 0,
  attendance_rate: 0, overtime_rate: 0, owed_rate: 0,
})

const yearMonth = ref('')
const teams = ref([])
const teamHours = ref([])
const changelog = ref([])
const dailyTrend = ref([])
const dailyProduction = ref([])
const teamProduction = ref([])

const trendDetailVisible = ref(false)
const trendDetailDate = ref('')
const trendDetailData = ref([])
const distDetailVisible = ref(false)
const distDetailTitle = ref('')
const distDetailData = ref([])
const allChangelogVisible = ref(false)
const allChangelogs = ref([])
const changelogDetailVisible = ref(false)
const currentChangelog = ref(null)
const dailyProdDetailVisible = ref(false)
const dailyProdDetailDate = ref('')
const dailyProdDetailData = ref([])

function statusType(s) {
  const m = { '正常': 'success', '迟到': 'warning', '缺勤': 'danger', '早退': 'warning', '请假': 'info', '休息': '' }
  return m[s] || 'info'
}

function showChangelogDetail(log) { currentChangelog.value = log; changelogDetailVisible.value = true }

async function showAllChangelog() {
  try { const r = await api.get('/announcements', { params: { type: '更新日志', limit: 100 } }); allChangelogs.value = r.data.items || [] } catch (e) { allChangelogs.value = [] }
  allChangelogVisible.value = true
}

const hoursTrendOptions = computed(() => {
  const data = dailyTrend.value
  const dates = data.map(d => d.date.slice(5))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['应出勤工时', '实际工时'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '20%', containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value' },
    series: [
      { name: '应出勤工时', type: 'line', data: data.map(d => d.scheduled_hours), smooth: true, itemStyle: { color: '#5470c6' }, lineStyle: { type: 'dashed' }, areaStyle: { opacity: 0.08 } },
      { name: '实际工时', type: 'line', data: data.map(d => d.actual_hours), smooth: true, itemStyle: { color: '#91cc75' }, areaStyle: { opacity: 0.15 } },
    ],
  }
})

const hoursDistOptions = computed(() => {
  const data = dailyTrend.value
  const dates = data.map(d => d.date.slice(5))
  return {
    tooltip: {
      trigger: 'axis',
      appendToBody: true,
      formatter: (params) => {
        const idx = params[0].dataIndex
        const d = data[idx]
        let s = `<b>${d.date}</b><br/>`
        const order = ['应到人数', '实到人数', '休息人数', '请假人数', '缺勤人数', '≥9h（加班）', '8~9h（正常）', '7~8h（略低）', '<7h（不足）']
        const pMap = {}
        params.forEach(p => { pMap[p.seriesName] = p })
        order.forEach(name => {
          const p = pMap[name]
          if (p) s += `${p.marker} ${name}：${p.value}<br/>`
        })
        return s
      }
    },
    legend: { data: ['≥9h（加班）', '8~9h（正常）', '7~8h（略低）', '<7h（不足）', '实到人数', '应到人数', '休息人数', '请假人数', '缺勤人数'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '22%', containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '≥9h（加班）', type: 'bar', stack: 'total', data: data.map(d => d.long_hours), itemStyle: { color: '#f56c6c' } },
      { name: '8~9h（正常）', type: 'bar', stack: 'total', data: data.map(d => d.normal_hours_count), itemStyle: { color: '#67c23a' } },
      { name: '7~8h（略低）', type: 'bar', stack: 'total', data: data.map(d => d.slight_short), itemStyle: { color: '#e6a23c' } },
      { name: '<7h（不足）', type: 'bar', stack: 'total', data: data.map(d => d.short_hours), itemStyle: { color: '#909399' } },
      { name: '实到人数', type: 'line', data: data.map(d => d.total_with_hours), smooth: true, lineStyle: { type: 'dashed', color: '#5470c6' }, itemStyle: { color: '#5470c6' }, symbol: 'circle', symbolSize: 4 },
      { name: '应到人数', type: 'line', data: data.map(d => d.expected_count), smooth: true, lineStyle: { type: 'dotted', color: '#fc8452' }, itemStyle: { color: '#fc8452' }, symbol: 'diamond', symbolSize: 4 },
      { name: '休息人数', type: 'line', data: data.map(d => d.timeoff), smooth: true, lineStyle: { type: 'dotted', color: '#b37feb' }, itemStyle: { color: '#b37feb' }, symbol: 'triangle', symbolSize: 4 },
      { name: '请假人数', type: 'line', data: data.map(d => d.leave), smooth: true, lineStyle: { type: 'dotted', color: '#69b1ff' }, itemStyle: { color: '#69b1ff' }, symbol: 'rect', symbolSize: 4 },
      { name: '缺勤人数', type: 'line', data: data.map(d => d.absent), smooth: true, lineStyle: { type: 'dotted', color: '#ff7875' }, itemStyle: { color: '#ff7875' }, symbol: 'pin', symbolSize: 4 },
    ],
  }
})

const mergedTeamOptions = computed(() => {
  const hoursData = teamHours.value.slice(0, 10)
  const prodMap = {}
  teamProduction.value.forEach(p => { prodMap[p.team] = p })
  const tiDanLv = hoursData.map(d => {
    const p = prodMap[d.team]
    return p?.call_count > 0 ? +(p.ticket_count / p.call_count * 100).toFixed(1) : 0
  })
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const idx = params[0].dataIndex
        const h = hoursData[idx]
        const p = prodMap[h?.team]
        if (!h) return ''
        let s = `<b>${h.team}</b>（${h.emp_count} 人）<br/>`
        const order = ['应出勤工时', '实际工时', '通话量', '提单率']
        const pMap = {}
        params.forEach(p => { pMap[p.seriesName] = p })
        order.forEach(name => {
          const pp = pMap[name]
          if (pp) s += `${pp.marker} ${name}：${name === '提单率' ? pp.value + '%' : pp.value}<br/>`
        })
        if (p) {
          s += `<span style="color:#999;font-size:12px">产量人数：${p.emp_count} | 工单量：${p.ticket_count}</span>`
        }
        return s
      }
    },
    legend: { data: ['应出勤工时', '实际工时', '通话量', '提单率'], bottom: 0 },
    grid: { left: '3%', right: '12%', bottom: '22%', containLabel: true },
    xAxis: { type: 'category', data: hoursData.map(d => `${d.team}\n(${d.emp_count}人)`) },
    yAxis: [
      { type: 'value', name: '工时(h)' },
      { type: 'value', name: '通话量', position: 'right' },
      { type: 'value', name: '提单率(%)', position: 'right', offset: 60, axisLabel: { formatter: '{value}%' }, splitLine: { show: false }, min: 0, max: 50 },
    ],
    series: [
      { name: '应出勤工时', type: 'bar', data: hoursData.map(d => d.scheduled_hours), itemStyle: { color: '#5470c6' } },
      { name: '实际工时', type: 'bar', data: hoursData.map(d => d.actual_hours), itemStyle: { color: '#91cc75' } },
      { name: '通话量', type: 'line', yAxisIndex: 1, data: hoursData.map(d => prodMap[d.team]?.call_count || 0), smooth: true, itemStyle: { color: '#ee6666' }, symbol: 'circle', symbolSize: 4 },
      { name: '提单率', type: 'line', yAxisIndex: 2, data: tiDanLv, smooth: true, itemStyle: { color: '#fac858' }, symbol: 'diamond', symbolSize: 6 },
    ],
  }
})

const dailyProdOptions = computed(() => {
  const data = dailyProduction.value
  const dates = data.map(d => d.date.slice(5))
  const tiDanLv = data.map(d => d.call_count > 0 ? +(d.ticket_count / d.call_count * 100).toFixed(1) : 0)
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const idx = params[0].dataIndex
        const d = data[idx]
        if (!d) return ''
        let s = `<b>${d.date}</b><br/>`
        const order = ['通话量', '工单量', '提单率']
        const pMap = {}
        params.forEach(p => { pMap[p.seriesName] = p })
        order.forEach(name => {
          const p = pMap[name]
          if (p) s += `${p.marker} ${name}：${name === '提单率' ? p.value + '%' : p.value}<br/>`
        })
        s += `<span style="color:#999;font-size:12px">人数：${d.people_count}</span>`
        return s
      }
    },
    legend: { data: ['通话量', '工单量', '提单率'], bottom: 0 },
    grid: { left: '3%', right: '12%', bottom: '22%', containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: [
      { type: 'value', name: '通话量' },
      { type: 'value', name: '工单量', position: 'right' },
      { type: 'value', name: '提单率(%)', position: 'right', offset: 60, axisLabel: { formatter: '{value}%' }, splitLine: { show: false }, min: 0, max: 50 },
    ],
    series: [
      { name: '通话量', type: 'bar', data: data.map(d => d.call_count), itemStyle: { color: '#5470c6' } },
      { name: '工单量', type: 'line', yAxisIndex: 1, data: data.map(d => d.ticket_count), smooth: true, itemStyle: { color: '#91cc75' }, areaStyle: { opacity: 0.15 } },
      { name: '提单率', type: 'line', yAxisIndex: 2, data: tiDanLv, smooth: true, itemStyle: { color: '#ee6666' }, symbol: 'diamond', symbolSize: 6 },
    ],
  }
})

async function handleTrendClick(params) {
  const idx = typeof params.dataIndex === 'number' ? params.dataIndex : 0
  const date = dailyTrend.value[idx]?.date
  if (!date) return
  trendDetailDate.value = date
  try {
    const r = await api.get('/daily-detail', { params: { date } })
    trendDetailData.value = r.data || []
  } catch (e) { trendDetailData.value = [] }
  trendDetailVisible.value = true
}

async function handleDistClick(params) {
  const idx = typeof params.dataIndex === 'number' ? params.dataIndex : 0
  const date = dailyTrend.value[idx]?.date
  const seriesName = params.seriesName || ''
  const bucketMap = { '≥9h（加班）': 'long', '8~9h（正常）': 'normal', '7~8h（略低）': 'slight', '<7h（不足）': 'short' }
  const bucket = bucketMap[seriesName]
  if (!date || !bucket) return
  distDetailTitle.value = `${date} ${seriesName}`
  try {
    const r = await api.get('/hour-bucket-detail', { params: { date, bucket } })
    distDetailData.value = r.data || []
  } catch (e) { distDetailData.value = [] }
  distDetailVisible.value = true
}

async function handleDailyProdClick(params) {
  const idx = typeof params.dataIndex === 'number' ? params.dataIndex : 0
  const entry = dailyProduction.value[idx]
  if (!entry || !entry.date) return
  dailyProdDetailDate.value = entry.date
  try {
    const r = await api.get('/workloads/report', { params: { start_date: entry.date, end_date: entry.date } })
    dailyProdDetailData.value = (r.data.items || []).map(item => ({
      account: item.account,
      name: item.name,
      team_desc: item.team_desc,
      call_count: item.aggregated_metrics['呼入人工服务-人工服务-通话次数'] || 0,
      ticket_count: item.aggregated_metrics['呼入人工服务-工单-生成总量'] || 0,
      outbound_count: item.aggregated_metrics['呼出服务-人工呼出呼叫量'] || 0,
    }))
  } catch {
    dailyProdDetailData.value = []
  }
  dailyProdDetailVisible.value = true
}

function onMonthChange() {
  loadAll()
}

async function loadStats() {
  try {
    const params = yearMonth.value ? { year_month: yearMonth.value } : {}
    const r = await api.get('/stats', { params })
    stats.value = r.data
  } catch (e) { /* keep defaults */ }
}

async function loadTeams() {
  try { const r = await api.get('/teams'); teams.value = r.data || [] } catch (e) { teams.value = [] }
}

async function loadChangelog() {
  try { const r = await api.get('/announcements/changelog'); changelog.value = r.data || [] } catch (e) { changelog.value = [] }
}

async function loadDailyTrend() {
  try {
    const params = yearMonth.value ? { year_month: yearMonth.value } : {}
    const r = await api.get('/daily-trend', { params })
    dailyTrend.value = r.data || []
  } catch (e) { dailyTrend.value = [] }
}

async function loadTeamHours() {
  try {
    const params = yearMonth.value ? { year_month: yearMonth.value } : {}
    const r = await api.get('/team-hours', { params })
    teamHours.value = r.data || []
  } catch (e) { teamHours.value = [] }
}

async function loadDailyProduction() {
  try {
    const params = yearMonth.value ? { year_month: yearMonth.value } : {}
    const r = await api.get('/workloads/daily-production', { params })
    dailyProduction.value = r.data || []
  } catch { dailyProduction.value = [] }
}

async function loadTeamProduction() {
  try {
    const params = yearMonth.value ? { year_month: yearMonth.value } : {}
    const r = await api.get('/workloads/team-production', { params })
    teamProduction.value = r.data || []
  } catch { teamProduction.value = [] }
}

async function loadAll() {
  await loadStats()
  await Promise.all([loadTeams(), loadChangelog(), loadDailyTrend(), loadTeamHours(), loadDailyProduction(), loadTeamProduction()])
}

onMounted(() => {
  const now = new Date()
  yearMonth.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  loadAll()
})
</script>

<style scoped>
.dashboard { width: 100%; }
.data-date-banner { margin-bottom: 0; }
.banner-content { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.date-info { display: flex; align-items: center; gap: 10px; }
.date-text { font-size: 14px; color: #333; }
.report-count { font-size: 13px; color: #999; }
.changelog-carousel { display: flex; align-items: center; gap: 8px; max-width: 350px; }
.carousel-inline { flex: 1; min-width: 150px; }
.carousel-item-content { display: flex; align-items: center; gap: 4px; }
.carousel-text { font-size: 13px; color: #666; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }
</style>