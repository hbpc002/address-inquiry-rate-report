<template>
  <div class="marketing-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.marketing_report }}</span>
          <el-button v-if="userStore.hasPermission('marketing_report.export')" type="success" size="small" @click="handleExport">导出当前维度</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="查询方式">
          <el-radio-group v-model="searchForm.type">
            <el-radio value="day">按天</el-radio>
            <el-radio value="month">按月</el-radio>
            <el-radio value="range">自定义</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'day'" label="竣工日期">
          <el-date-picker v-model="searchForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'month'" label="竣工月份">
          <el-date-picker v-model="searchForm.month" type="month" value-format="YYYY-MM" placeholder="选择月份" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="开始日期">
          <el-date-picker v-model="searchForm.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="结束日期">
          <el-date-picker v-model="searchForm.end_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="数据来源">
          <el-select v-model="searchForm.data_type" placeholder="全部来源" clearable style="width: 120px">
            <el-option v-for="item in options.sources" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="行分类">
          <el-select v-model="searchForm.group_name" placeholder="全部行分类" clearable filterable style="width: 160px">
            <el-option v-for="g in options.groups" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门组">
          <el-select v-model="searchForm.department_group" placeholder="全部部门组" clearable filterable style="width: 170px">
            <el-option v-for="group in options.department_groups" :key="group" :label="group" :value="group" />
          </el-select>
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="searchForm.team_key" placeholder="全部班组" clearable filterable style="width: 180px" @change="handleTeamFilterChange">
            <el-option v-for="t in filteredTeamOptions" :key="t.team_key" :label="t.team_label" :value="t.team_key" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="searchForm.class_key" placeholder="全部班级" clearable filterable style="width: 180px" @change="handleClassFilterChange">
            <el-option v-for="c in filteredClassOptions" :key="c.class_key" :label="c.class_label" :value="c.class_key" />
          </el-select>
        </el-form-item>
        <el-form-item label="重点业务">
          <el-select v-model="searchForm.business_type" placeholder="全部业务" clearable style="width: 120px">
            <el-option label="叠加包" value="叠加包" />
            <el-option label="套餐变更" value="套餐变更" />
          </el-select>
        </el-form-item>
        <el-form-item label="来话/去话">
          <el-select v-model="searchForm.lh_qh" placeholder="全部" clearable style="width: 100px">
            <el-option label="来话" value="来话" />
            <el-option label="去话" value="去话" />
          </el-select>
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="姓名" clearable style="width: 110px" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="searchForm.emp_no" placeholder="工号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-row class="stats-row">
        <div class="stat-item"><el-statistic title="产品办理量" :value="stats.total" /></div>
        <div class="stat-item"><el-statistic title="订单数" :value="stats.order_count" /></div>
        <div class="stat-item"><el-statistic title="来话办理量" :value="stats.inbound" /></div>
        <div class="stat-item"><el-statistic title="去话办理量" :value="stats.outbound" /></div>
        <div class="stat-item"><el-statistic title="叠加包" :value="stats.overlay" /></div>
        <div class="stat-item"><el-statistic title="套餐变更" :value="stats.package_change" /></div>
        <div class="stat-item"><el-statistic title="涉及员工" :value="stats.people_count" /></div>
      </el-row>

      <div v-if="stats.total > 0" class="chart-section">
        <div class="chart-section-header">
          <span class="chart-section-title">图表分析</span>
          <el-radio-group v-model="chartSection" size="small">
            <el-radio-button value="team">班组分析</el-radio-button>
            <el-radio-button value="trend">趋势分析</el-radio-button>
            <el-radio-button value="auxiliary">辅助维度</el-radio-button>
          </el-radio-group>
        </div>

        <template v-if="chartSection === 'team'">
          <div class="chart-toolbar">
            <span>排行指标</span>
            <el-radio-group v-model="teamMetric" size="small">
              <el-radio-button v-for="item in teamRankingMetrics" :key="item.key" :value="item.key">
                {{ item.label }}
              </el-radio-button>
            </el-radio-group>
            <span>结构维度</span>
            <el-radio-group v-model="teamStructureKind" size="small">
              <el-radio-button value="business">业务结构</el-radio-button>
              <el-radio-button value="lh">来话/去话结构</el-radio-button>
            </el-radio-group>
            <span>Top N</span>
            <el-select v-model="teamLimit" size="small" style="width: 90px">
              <el-option v-for="limit in topLimits" :key="limit" :label="String(limit)" :value="limit" />
            </el-select>
            <span v-if="teamDrillActive" class="drill-hint">当前：{{ drillTeamLabel }} 组员，点击图表返回班组</span>
          </div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="teamRankingOptions" height="300px" @click="handleTeamChartClick" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="teamStructureOptions" height="300px" @click="handleTeamChartClick" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="teamValidOptions" height="300px" @click="handleTeamChartClick" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="teamRadarOptions" height="320px" @click="handleTeamChartClick" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="teamScatterOptions" height="320px" @click="handleTeamChartClick" />
              </el-card>
            </el-col>
          </el-row>
        </template>

        <template v-else-if="chartSection === 'trend'">
          <el-row :gutter="16">
            <el-col :span="24" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="dailyTrendOptions" height="340px" />
              </el-card>
            </el-col>
            <el-col :xs="24" :lg="12" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="dailyBusinessOptions" height="300px" />
              </el-card>
            </el-col>
            <el-col :xs="24" :lg="12" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="dailyLhOptions" height="300px" />
              </el-card>
            </el-col>
            <el-col :xs="24" :lg="12" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="dailyValidOptions" height="300px" />
              </el-card>
            </el-col>
            <el-col :xs="24" :lg="12" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="dailyOrderRateOptions" height="300px" />
              </el-card>
            </el-col>
          </el-row>
        </template>

        <template v-else>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="productRankingOptions" height="320px" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="groupRankingOptions" height="320px" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="productBusinessOptions" height="320px" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="productLhOptions" height="320px" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="groupBusinessOptions" height="320px" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8" class="chart-col">
              <el-card shadow="hover" class="chart-card">
                <Echart :options="groupLhOptions" height="320px" />
              </el-card>
            </el-col>
          </el-row>
        </template>
      </div>

      <el-tabs v-model="dimension" @tab-change="handleDimensionChange">
        <el-tab-pane label="员工" name="employee" />
        <el-tab-pane label="班组" name="team" />
        <el-tab-pane label="行分类" name="group" />
        <el-tab-pane label="产品" name="product" />
        <el-tab-pane label="按日趋势" name="day" />
      </el-tabs>

      <el-table v-loading="drillLoading" :data="tableData" border stripe max-height="calc(100vh - 520px)">
        <template v-if="dimension === 'employee'">
          <el-table-column prop="kf_id" label="客服工号" width="120" sortable />
          <el-table-column prop="name" label="姓名" width="90" sortable />
          <el-table-column prop="team" label="班组" width="110" show-overflow-tooltip sortable />
          <el-table-column prop="dept" label="部门" width="140" show-overflow-tooltip sortable />
          <el-table-column prop="group_name" label="行分类" width="120" show-overflow-tooltip sortable />
        </template>
        <template v-else-if="dimension === 'team'">
          <el-table-column prop="team_label" label="班组" width="180" show-overflow-tooltip sortable />
          <el-table-column prop="leader" label="组长" width="90" show-overflow-tooltip sortable />
          <el-table-column prop="people" label="人数" width="80" sortable />
        </template>
        <template v-else-if="dimension === 'group'">
          <el-table-column prop="group_name" label="行分类" width="130" show-overflow-tooltip sortable />
          <el-table-column prop="people" label="人数" width="80" sortable />
        </template>
        <template v-else-if="dimension === 'product'">
          <el-table-column prop="product_id" label="产品ID" width="120" sortable />
          <el-table-column prop="product_name" label="产品名称" min-width="240" show-overflow-tooltip sortable />
        </template>
        <template v-else>
          <el-table-column prop="date" label="竣工日期" width="120" sortable />
        </template>
        <el-table-column prop="total" label="产品办理量" width="110" sortable />
        <el-table-column prop="order_count" label="订单数" width="90" sortable />
        <el-table-column prop="inbound" label="来话办理量" width="110" sortable />
        <el-table-column prop="outbound" label="去话办理量" width="110" sortable />
        <el-table-column prop="overlay" label="叠加包" width="90" sortable />
        <el-table-column prop="overlay_day" label="日包" width="80" sortable />
        <el-table-column prop="overlay_month" label="月包" width="80" sortable />
        <el-table-column prop="overlay_long" label="长期包" width="90" sortable />
        <el-table-column prop="overlay_undefined" label="未定义" width="90" sortable />
        <el-table-column prop="package_change" label="套餐变更" width="100" sortable />
        <el-table-column v-if="dimension !== 'product'" prop="opening_rate" label="开口率" width="100" sortable>
          <template #default="{ row }">
            {{ formatOpeningRate(row.opening_rate) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { api, useUserStore } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage } from 'element-plus'
import { downloadBlob } from '../utils/download'
import { decorateClassOptions, decorateTeamOptions, decorateTeamRows, findClassOption, findTeamOption, teamKey } from '../utils/teamIdentity'
import Echart from '../components/Echart.vue'
import {
  RANKING_METRICS,
  TOP_LIMITS,
  enrichEmployees,
  enrichTeams,
  enrichGroups,
  enrichProducts,
  filterMatchedTeams,
  metricLabel,
  buildTeamRankingOptions,
  buildEmployeeRankingOptions,
  buildProductRankingOptions,
  buildGroupRankingOptions,
  buildBusinessCrossOptions,
  buildLhCrossOptions,
  buildValidCrossOptions,
  buildDailyTrendOptions,
  buildDailyBusinessOptions,
  buildDailyLhOptions,
  buildDailyValidOptions,
  buildDailyOrderRateOptions,
  buildTeamScatterOptions,
  buildEmployeeScatterOptions,
  buildTeamRadarOptions,
  buildMemberRadarOptions
} from '../utils/marketingCharts'

const userStore = useUserStore()
const ui = useUiConfigStore()
const now = new Date()
const defaultMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
const searchForm = reactive({
  type: 'month',
  date: '',
  month: defaultMonth,
  start_date: '',
  end_date: '',
  group_name: '',
  data_type: '',
  department_group: '',
  team_key: '',
  class_key: '',
  business_type: '',
  lh_qh: '',
  name: '',
  emp_no: ''
})
const stats = reactive({
  total: 0,
  order_count: 0,
  inbound: 0,
  outbound: 0,
  overlay: 0,
  package_change: 0,
  people_count: 0
})
const options = reactive({ groups: [], teams: [], department_groups: [], team_options: [], classes: [], class_options: [], orgs: [], products: [], sources: [] })
const result = ref({ employees: [], teams: [], groups: [], products: [], days: [] })
const filteredTeamOptions = computed(() => searchForm.department_group
  ? options.team_options.filter(item => item.dept_group === searchForm.department_group)
  : options.team_options)
const filteredClassOptions = computed(() => searchForm.department_group
  ? options.class_options.filter(item => item.dept_group === searchForm.department_group)
  : options.class_options)
const decoratedTeams = computed(() => decorateTeamRows(result.value.teams || []))
const dimension = ref('employee')
const dimensionKey = computed(() => ({ employee: 'employees', team: 'teams', group: 'groups', product: 'products', day: 'days' }[dimension.value]))
const chartSection = ref('team')
const teamMetric = ref('total')
const teamStructureKind = ref('business')
const teamLimit = ref(10)
const drillTeamKey = ref('')
const drillResult = ref(null)
const drillLoading = ref(false)
let drillRequestId = 0
const TEAM_RANKING_KEYS = ['total', 'avg_total', 'avg_order', 'order_rate']
const teamRankingMetrics = RANKING_METRICS.filter(item => TEAM_RANKING_KEYS.includes(item.key))
const topLimits = TOP_LIMITS

const teamItems = computed(() => filterMatchedTeams(decoratedTeams.value))
const groupItems = computed(() => enrichGroups(result.value.groups || []))
const productItems = computed(() => enrichProducts(result.value.products || []))
const dayItems = computed(() => result.value.days || [])

const drillTeam = computed(() => decoratedTeams.value.find(item => item.team_key === drillTeamKey.value) || null)
const drillTeamLabel = computed(() => drillTeam.value?.team_label || drillTeam.value?.team || '')
const teamDrillActive = computed(() => Boolean(drillTeamKey.value))
const teamMemberItems = computed(() => {
  if (!drillTeamKey.value) return []
  const members = (result.value.employees || []).filter(item => teamKey(item.dept, item.team) === drillTeamKey.value)
  return enrichEmployees(members)
})

const tableData = computed(() => {
  if (teamDrillActive.value) {
    if (drillResult.value) {
      return dimension.value === 'team'
        ? decorateTeamRows(drillResult.value.teams || [])
        : (drillResult.value[dimensionKey.value] || [])
    }
    if (dimension.value === 'employee') return teamMemberItems.value
    if (dimension.value === 'team') return decorateTeamRows(decoratedTeams.value.filter(item => item.team_key === drillTeamKey.value))
    return []
  }
  return dimension.value === 'team' ? decoratedTeams.value : (result.value[dimensionKey.value] || [])
})

const teamRankingOptions = computed(() => {
  if (teamDrillActive.value) {
    return buildEmployeeRankingOptions(teamMemberItems.value, {
      metric: teamMetric.value,
      limit: teamLimit.value,
      title: `${drillTeamLabel.value} 组员${metricLabel(teamMetric.value)}排行`
    })
  }
  return buildTeamRankingOptions(teamItems.value, {
    metric: teamMetric.value,
    limit: teamLimit.value
  })
})
const teamStructureOptions = computed(() => {
  const items = teamDrillActive.value ? teamMemberItems.value : teamItems.value
  const prefix = teamDrillActive.value ? `${drillTeamLabel.value} 组员` : '班组'
  if (teamStructureKind.value === 'lh') {
    return buildLhCrossOptions(items, {
      title: `${prefix}来话/去话结构`,
      limit: teamLimit.value
    })
  }
  return buildBusinessCrossOptions(items, {
    title: `${prefix}业务结构`,
    limit: teamLimit.value
  })
})
const teamValidOptions = computed(() => {
  const items = teamDrillActive.value ? teamMemberItems.value : teamItems.value
  const prefix = teamDrillActive.value ? `${drillTeamLabel.value} 组员` : '班组'
  return buildValidCrossOptions(items, {
    title: `${prefix}叠加包有效期结构`,
    limit: teamLimit.value
  })
})
const teamRadarOptions = computed(() => {
  if (teamDrillActive.value) {
    return buildMemberRadarOptions(teamMemberItems.value, {
      title: `${drillTeamLabel.value} 组员多指标雷达`,
      limit: 8
    })
  }
  return buildTeamRadarOptions(teamItems.value, { limit: 8 })
})
const teamScatterOptions = computed(() => {
  if (teamDrillActive.value) {
    return buildEmployeeScatterOptions(teamMemberItems.value, {
      title: `${drillTeamLabel.value} 组员办理量与订单数分布`
    })
  }
  return buildTeamScatterOptions(teamItems.value)
})

const dailyTrendOptions = computed(() => buildDailyTrendOptions(dayItems.value))
const dailyBusinessOptions = computed(() => buildDailyBusinessOptions(dayItems.value))
const dailyLhOptions = computed(() => buildDailyLhOptions(dayItems.value))
const dailyValidOptions = computed(() => buildDailyValidOptions(dayItems.value))
const dailyOrderRateOptions = computed(() => buildDailyOrderRateOptions(dayItems.value))

const productRankingOptions = computed(() => buildProductRankingOptions(productItems.value, {
  metric: 'total',
  limit: 10,
  title: '产品办理量排行'
}))
const groupRankingOptions = computed(() => buildGroupRankingOptions(groupItems.value, {
  metric: 'total',
  limit: 10,
  title: '行分类办理量排行'
}))
const productBusinessOptions = computed(() => buildBusinessCrossOptions(productItems.value, {
  title: '产品业务结构',
  limit: 10
}))
const productLhOptions = computed(() => buildLhCrossOptions(productItems.value, {
  title: '产品来话/去话结构',
  limit: 10
}))
const groupBusinessOptions = computed(() => buildBusinessCrossOptions(groupItems.value, {
  title: '行分类业务结构',
  limit: 10
}))
const groupLhOptions = computed(() => buildLhCrossOptions(groupItems.value, {
  title: '行分类来话/去话结构',
  limit: 10
}))

function buildParams() {
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
  for (const key of ['group_name', 'data_type', 'department_group', 'business_type', 'lh_qh', 'name', 'emp_no']) {
    if (searchForm[key]) params[key] = searchForm[key]
  }
  const team = findTeamOption(options.team_options, searchForm.team_key)
  const className = findClassOption(options.class_options, searchForm.class_key)
  if (team) {
    params.dept = team.dept
    params.team = team.team
  } else if (className) {
    params.dept = className.dept
    params.class_name = className.class_name
  }
  return params
}

function clearTeamDrill() {
  drillRequestId += 1
  drillTeamKey.value = ''
  drillResult.value = null
  drillLoading.value = false
}

async function loadDrillData(key) {
  const team = decoratedTeams.value.find(item => item.team_key === key)
  if (!team) return
  const requestId = ++drillRequestId
  drillLoading.value = true
  try {
    const res = await api.get('/marketing/report', {
      params: { ...buildParams(), dept: team.dept, team: team.team }
    })
    if (requestId !== drillRequestId || drillTeamKey.value !== key) return
    drillResult.value = res.data
  } catch (e) {
    if (requestId === drillRequestId) {
      ElMessage.error(e.response?.data?.detail || '班组明细加载失败')
    }
  } finally {
    if (requestId === drillRequestId) drillLoading.value = false
  }
}

async function loadData() {
  clearTeamDrill()
  try {
    const res = await api.get('/marketing/report', { params: buildParams() })
    Object.assign(stats, res.data.stats)
    result.value = res.data
    Object.assign(options, res.data.options || {})
    const rawTeamOptions = res.data.options?.team_options?.length
      ? res.data.options.team_options
      : (res.data.options?.teams || []).map(team => ({ dept: '', team }))
    const rawClassOptions = res.data.options?.class_options?.length
      ? res.data.options.class_options
      : (res.data.options?.classes || []).map(className => ({ dept: '', class_name: className }))
    options.team_options = decorateTeamOptions(rawTeamOptions)
    options.class_options = decorateClassOptions(rawClassOptions)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

function resetFilters() {
  Object.assign(searchForm, {
    type: 'month',
    date: '',
    month: defaultMonth,
    start_date: '',
    end_date: '',
    group_name: '',
    data_type: '',
    department_group: '',
    team_key: '',
    class_key: '',
    business_type: '',
    lh_qh: '',
    name: '',
    emp_no: ''
  })
  loadData()
}

function handleTeamChartClick(params) {
  if (drillTeamKey.value) {
    if (params?.name || params?.data) clearTeamDrill()
    return
  }
  const teamData = params?.data || {}
  const key = teamData.team_key || decoratedTeams.value.find(item => item.team_label === params?.name || item.team === params?.name)?.team_key
  if (!key) return
  drillTeamKey.value = key
  drillResult.value = null
  loadDrillData(key)
}

function formatOpeningRate(value) {
  if (value == null) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function handleDimensionChange() {
  if (!teamDrillActive.value) loadData()
}

function handleTeamFilterChange(value) {
  if (value) searchForm.class_key = ''
  loadData()
}

function handleClassFilterChange(value) {
  if (value) searchForm.team_key = ''
  loadData()
}

function handleExport() {
  const params = { ...buildParams(), dimension: dimension.value }
  if (drillTeam.value) {
    params.dept = drillTeam.value.dept
    params.team = drillTeam.value.team
  }
  downloadBlob('/marketing/report/export', params, 'marketing_report.csv')
}

watch(() => searchForm.team_key, (value) => {
  if (value) searchForm.class_key = ''
})
watch(() => searchForm.class_key, (value) => {
  if (value) searchForm.team_key = ''
})
watch(() => searchForm.department_group, (value) => {
  if (!value) return
  const team = findTeamOption(options.team_options, searchForm.team_key)
  if (team && team.dept_group !== value) searchForm.team_key = ''
  const className = findClassOption(options.class_options, searchForm.class_key)
  if (className && className.dept_group !== value) searchForm.class_key = ''
})

watch(decoratedTeams, (teams) => {
  if (drillTeamKey.value && !teams.some(item => item.team_key === drillTeamKey.value)) {
    clearTeamDrill()
  }
})

onMounted(loadData)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stats-row {
  display: flex;
  flex-wrap: nowrap;
  gap: 20px;
  margin-bottom: 16px;
}
.stat-item {
  flex: 1 1 0;
  min-width: 0;
}
.chart-section {
  margin-bottom: 16px;
}
.chart-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}
.chart-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.chart-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  color: #606266;
  font-size: 13px;
}
.drill-hint {
  color: #409eff;
}
.chart-col {
  margin-bottom: 16px;
}
.chart-col :deep(.chart-card) {
  border: 1px solid #ebeef5;
  border-radius: 6px;
}
</style>
