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
          <el-button v-if="userStore.hasPermission('reports.dashboard_export')" type="success" size="small" @click="exportDashboard">导出</el-button>
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

    <el-row :gutter="12" style="margin-top:20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>休息/示忙分析</span>
              <el-radio-group v-model="stateTab" size="small">
                <el-radio-button value="trend">总体趋势</el-radio-button>
                <el-radio-button value="team">班组对比</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <ChartPanel fullscreenable>
            <div v-if="stateTab === 'team'" style="display:flex;justify-content:flex-end;margin-bottom:4px">
              <el-radio-group v-model="stateMetric" size="small">
                <el-radio-button value="count">次数</el-radio-button>
                <el-radio-button value="duration">时长</el-radio-button>
                <el-radio-button value="freq">频次</el-radio-button>
              </el-radio-group>
            </div>
            <Echart v-if="stateTab === 'trend'" :options="dailyStateOptions" :height="320" @click="handleDailyStateClick" />
            <Echart v-else :options="teamStateOptions" :height="300" @click="handleTeamStateClick" />
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

    <el-dialog v-model="stateDetailVisible" :title="'示忙休息明细 - ' + stateDetailDate" width="900px">
      <el-tabs v-model="stateDetailTab">
        <el-tab-pane label="班组汇总" name="team">
          <el-table :data="stateTeamSummary" border stripe max-height="460">
            <el-table-column prop="team" label="班组" min-width="140" />
            <el-table-column prop="busy_count" label="示忙次数" width="90" sortable />
            <el-table-column prop="busy_hours" label="示忙时长(h)" width="100" sortable />
            <el-table-column prop="rest_count" label="休息次数" width="90" sortable />
            <el-table-column prop="rest_hours" label="休息时长(h)" width="100" sortable />
            <el-table-column prop="freq" label="频次(次/人)" width="100" sortable />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="个人明细" name="person">
          <el-table :data="statePersonDetail" border stripe max-height="460">
            <el-table-column prop="name" label="姓名" width="80" />
            <el-table-column prop="account" label="账号" width="110" />
            <el-table-column prop="team_desc" label="班组" min-width="140" />
            <el-table-column prop="busy_count" label="示忙次数" width="90" sortable />
            <el-table-column prop="busy_hours" label="示忙时长(h)" width="100" sortable />
            <el-table-column prop="rest_count" label="休息次数" width="90" sortable />
            <el-table-column prop="rest_hours" label="休息时长(h)" width="100" sortable />
            <el-table-column prop="freq" label="频次(次/人)" width="100" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
      <template #footer><el-button @click="stateDetailVisible = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="stateTeamDetailVisible" :title="stateTeamDetailTitle" width="900px">
      <el-table :data="stateTeamPersons" border stripe max-height="500">
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column prop="account" label="账号" width="110" />
        <el-table-column prop="team_desc" label="班组" min-width="140" />
        <el-table-column prop="busy_count" label="示忙次数" width="90" sortable />
        <el-table-column prop="busy_hours" label="示忙时长(h)" width="100" sortable />
        <el-table-column prop="rest_count" label="休息次数" width="90" sortable />
        <el-table-column prop="rest_hours" label="休息时长(h)" width="100" sortable />
        <el-table-column prop="freq" label="频次(次/人)" width="100" />
      </el-table>
      <div v-if="!stateTeamPersons.length" style="text-align:center;padding:40px;color:#999">该班组当月无数据</div>
      <template #footer><el-button @click="stateTeamDetailVisible = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../stores/user'
import { useUserStore } from '../stores/user'
const userStore = useUserStore()
import Echart from '../components/Echart.vue'
import ChartPanel from '../components/ChartPanel.vue'
import { downloadBlob } from '../utils/download'


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

const dailyStateTrend = ref([])
const monthlyReport = ref([])
const stateTab = ref('trend')
const stateMetric = ref('count')
const stateDetailVisible = ref(false)
const stateDetailDate = ref('')
const stateDetailTab = ref('team')
const stateDayItems = ref([])
const stateTeamDetailVisible = ref(false)
const stateTeamDetailTitle = ref('')
const stateTeamPersons = ref([])

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
    grid: { left: '3%', right: '12%', bottom: 45, containLabel: true },
    xAxis: { type: 'category', data: hoursData.map(d => d.team), axisLabel: { interval: 0, rotate: 28, margin: 8 } },
    yAxis: [
      { type: 'value', name: '工时(h)' },
      { type: 'value', name: '通话量', position: 'right' },
      { type: 'value', name: '提单率(%)', position: 'right', offset: 60, axisLabel: { formatter: '{value}%' }, splitLine: { show: false }, min: 10, max: 25 },
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
      { type: 'value', name: '提单率(%)', position: 'right', offset: 60, axisLabel: { formatter: '{value}%' }, splitLine: { show: false }, min: 10, max: 25 },
    ],
    series: [
      { name: '通话量', type: 'bar', data: data.map(d => d.call_count), itemStyle: { color: '#5470c6' } },
      { name: '工单量', type: 'line', yAxisIndex: 1, data: data.map(d => d.ticket_count), smooth: true, itemStyle: { color: '#91cc75' }, areaStyle: { opacity: 0.15 } },
      { name: '提单率', type: 'line', yAxisIndex: 2, data: tiDanLv, smooth: true, itemStyle: { color: '#ee6666' }, symbol: 'diamond', symbolSize: 6 },
    ],
  }
})

const dailyStateOptions = computed(() => {
  const data = dailyStateTrend.value
  const dates = data.map(d => d.date.slice(5))
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const idx = params[0].dataIndex
        const d = data[idx]
        if (!d) return ''
        let s = `<b>${d.date}</b><br/>`
        const order = ['示忙次数', '休息次数', '示忙时长(h)', '休息时长(h)']
        const pMap = {}
        params.forEach(p => { pMap[p.seriesName] = p })
        order.forEach(name => {
          const p = pMap[name]
          if (p) s += `${p.marker} ${name}：${p.value}<br/>`
        })
        s += `<span style="color:#999;font-size:12px">频次：示忙 ${d.busy_freq} 次/人 | 休息 ${d.rest_freq} 次/人 | 人数：${d.people_count}</span>`
        return s
      }
    },
    legend: { data: ['示忙次数', '休息次数', '示忙时长(h)', '休息时长(h)'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '22%', containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: [
      { type: 'value', name: '次数' },
      { type: 'value', name: '时长(h)', position: 'right' },
    ],
    series: [
      { name: '示忙次数', type: 'bar', data: data.map(d => d.busy_count), itemStyle: { color: '#5470c6' } },
      { name: '休息次数', type: 'bar', data: data.map(d => d.rest_count), itemStyle: { color: '#91cc75' } },
      { name: '示忙时长(h)', type: 'line', yAxisIndex: 1, data: data.map(d => +(d.busy_seconds / 3600).toFixed(2)), smooth: true, itemStyle: { color: '#ee6666' }, areaStyle: { opacity: 0.1 } },
      { name: '休息时长(h)', type: 'line', yAxisIndex: 1, data: data.map(d => +(d.rest_seconds / 3600).toFixed(2)), smooth: true, itemStyle: { color: '#fac858' }, areaStyle: { opacity: 0.1 } },
    ],
  }
})

const teamStateSummary = computed(() => {
  const persons = monthlyReport.value.map(extractStatePerson)
  return groupStateByTeam(persons).sort((a, b) => b.busy_count - a.busy_count)
})

const teamStateOptions = computed(() => {
  const teams = teamStateSummary.value.slice(0, 12)
  const metric = stateMetric.value
  const busyData = teams.map(t => metric === 'count' ? t.busy_count : metric === 'duration' ? t.busy_hours : +(t.busy_count / (t.people || 1)).toFixed(2))
  const restData = teams.map(t => metric === 'count' ? t.rest_count : metric === 'duration' ? t.rest_hours : +(t.rest_count / (t.people || 1)).toFixed(2))
  const unit = metric === 'count' ? '次' : metric === 'duration' ? 'h' : '次/人'
  const teamMap = {}
  teams.forEach(t => { teamMap[t.team] = t })
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const t = teamMap[params[0].name]
        if (!t) return ''
        let s = `<b>${t.team}</b>（${t.people} 人）<br/>`
        params.forEach(p => { s += `${p.marker} ${p.seriesName}：${p.value} ${unit}<br/>` })
        return s
      }
    },
    legend: { data: ['示忙', '休息'], bottom: 0 },
    grid: { left: '3%', right: '6%', bottom: 30, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: teams.map(t => t.team).reverse(), axisLabel: { interval: 0 } },
    series: [
      { name: '示忙', type: 'bar', data: busyData.slice().reverse(), itemStyle: { color: '#5470c6' } },
      { name: '休息', type: 'bar', data: restData.slice().reverse(), itemStyle: { color: '#91cc75' } },
    ],
  }
})

const stateTeamSummary = computed(() => groupStateByTeam(stateDayItems.value))
const statePersonDetail = computed(() => stateDayItems.value.map(p => ({ ...p, freq: 1 })))

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

const STATE_FIELDS = {
  busy_count: '操作次数及时长-示忙次数',
  busy_seconds: '操作次数及时长-示忙时长(秒)',
  rest_count: '操作次数及时长-休息次数',
  rest_seconds: '操作次数及时长-休息时长(秒)',
}

function extractStatePerson(item) {
  const m = item.aggregated_metrics || {}
  const busyCount = m[STATE_FIELDS.busy_count] || 0
  const restCount = m[STATE_FIELDS.rest_count] || 0
  return {
    account: item.account,
    name: item.name,
    team_desc: item.team_desc,
    busy_count: busyCount,
    busy_hours: +(((m[STATE_FIELDS.busy_seconds] || 0) / 3600)).toFixed(2),
    rest_count: restCount,
    rest_hours: +(((m[STATE_FIELDS.rest_seconds] || 0) / 3600)).toFixed(2),
    freq: 1,
  }
}

function groupStateByTeam(persons) {
  const map = {}
  persons.forEach(p => {
    const team = p.team_desc || '未知班组'
    if (!map[team]) map[team] = { team, busy_count: 0, busy_hours: 0, rest_count: 0, rest_hours: 0, _people: new Set() }
    map[team].busy_count += p.busy_count
    map[team].busy_hours = +(map[team].busy_hours + p.busy_hours).toFixed(2)
    map[team].rest_count += p.rest_count
    map[team].rest_hours = +(map[team].rest_hours + p.rest_hours).toFixed(2)
    map[team]._people.add(p.account)
  })
  return Object.values(map).map(t => ({
    team: t.team,
    busy_count: t.busy_count,
    busy_hours: t.busy_hours,
    rest_count: t.rest_count,
    rest_hours: t.rest_hours,
    people: t._people.size,
    freq: t._people.size ? +(t.busy_count / t._people.size).toFixed(2) : 0,
  }))
}

async function handleDailyStateClick(params) {
  if (!params || params.componentType !== 'series') return
  const idx = typeof params.dataIndex === 'number' ? params.dataIndex : 0
  const entry = dailyStateTrend.value[idx]
  if (!entry || !entry.date) return
  stateDetailDate.value = entry.date
  stateDetailTab.value = 'team'
  try {
    const r = await api.get('/workloads/report', { params: { start_date: entry.date, end_date: entry.date } })
    stateDayItems.value = (r.data.items || []).map(extractStatePerson)
  } catch {
    stateDayItems.value = []
  }
  stateDetailVisible.value = true
}

async function handleTeamStateClick(params) {
  if (!params || params.componentType !== 'series' || !params.name) return
  const teamName = params.name
  let items = monthlyReport.value
  if (!items.length) {
    try {
      const r = await api.get('/workloads/report', { params: yearMonth.value ? { year_month: yearMonth.value } : {} })
      items = r.data.items || []
      monthlyReport.value = items
    } catch { items = [] }
  }
  const persons = items
    .filter(i => (i.team_desc || '未知班组') === teamName)
    .map(extractStatePerson)
  stateTeamDetailTitle.value = `${teamName} - ${yearMonth.value || '本月'} 个人明细`
  stateTeamPersons.value = persons
  stateTeamDetailVisible.value = true
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

async function loadDailyStateTrend() {
  try {
    const params = yearMonth.value ? { year_month: yearMonth.value } : {}
    const r = await api.get('/workloads/daily-state-trend', { params })
    dailyStateTrend.value = r.data || []
  } catch { dailyStateTrend.value = [] }
}

async function loadMonthlyReport() {
  try {
    const params = yearMonth.value ? { year_month: yearMonth.value } : {}
    const r = await api.get('/workloads/report', { params })
    monthlyReport.value = r.data.items || []
  } catch { monthlyReport.value = [] }
}

async function loadAll() {
  await loadStats()
  await Promise.all([loadTeams(), loadChangelog(), loadDailyTrend(), loadTeamHours(), loadDailyProduction(), loadTeamProduction(), loadDailyStateTrend(), loadMonthlyReport()])
}

function exportDashboard() {
  const params = {}
  if (yearMonth.value) params.year_month = yearMonth.value
  downloadBlob('/reports/dashboard-export', params, `dashboard_${yearMonth.value || 'current'}.csv`)
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