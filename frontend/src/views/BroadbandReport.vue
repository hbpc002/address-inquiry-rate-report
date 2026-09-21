<template>
  <div class="broadband-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ pageTitle }}</span>
          <span>
            <el-button v-if="userStore.hasPermission('broadband_report.export')" type="success" size="small" @click="handleExport">导出</el-button>
          </span>
        </div>
      </template>

      <el-form v-show="!scatterFocus" inline>
        <el-form-item label="查询方式">
          <el-radio-group v-model="searchForm.type">
            <el-radio value="day">按天</el-radio>
            <el-radio value="month">按月</el-radio>
            <el-radio value="range">自定义</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <el-form v-show="!scatterFocus" inline>
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
          <el-select v-model="searchForm.team" placeholder="全部班组" clearable filterable style="width: 150px">
            <el-option v-for="t in stats.teams" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="searchForm.class_name" placeholder="全部班级" clearable filterable style="width: 120px">
            <el-option v-for="c in stats.classes" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="地市">
          <el-select v-model="searchForm.city" placeholder="全部地市" clearable filterable style="width: 110px">
            <el-option v-for="c in stats.cities" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-row :gutter="20" class="stats-row" v-show="!scatterFocus">
        <el-col :span="6">
          <el-statistic title="总人数" :value="stats.total_people" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="推荐量(意向单)" :value="stats.total_recommend" :precision="0" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="成功推荐" :value="stats.total_completed" :precision="0" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="平均成功率(%)" :value="avgSuccessRate" :precision="2" />
        </el-col>
      </el-row>

      <el-row v-if="tableData.length" style="margin-bottom: 16px">
        <el-col :span="24">
          <el-card shadow="hover">
            <div class="scatter-wrap">
              <div v-show="scatterFocus" class="stats-overlay" @click.stop>
                <el-statistic title="总人数" :value="stats.total_people" />
                <el-statistic title="推荐量(意向单)" :value="stats.total_recommend" :precision="0" />
                <el-statistic title="成功推荐" :value="stats.total_completed" :precision="0" />
                <el-statistic title="平均成功率(%)" :value="avgSuccessRate" :precision="2" />
              </div>
              <Echart :options="scatterOptions" :height="scatterHeight" @click="toggleScatterFocus" />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" v-if="tableData.length">
        <el-col :span="8">
          <el-card shadow="hover">
            <Echart :options="teamChartOptions" height="360px" @click="handlePieClick" />
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-table
            :data="paginatedData"
            border stripe
            max-height="calc(100vh - 560px)"
            @sort-change="handleSortChange"
          >
            <el-table-column label="排名" width="60" type="index" />
            <el-table-column prop="emp_no" label="工号" width="120" sortable="custom" />
            <el-table-column prop="name" label="姓名" width="90" sortable="custom" />
            <el-table-column prop="team" label="班组" min-width="150" sortable="custom" />
            <el-table-column prop="intention_count" label="意向单数量" width="110" sortable="custom" />
            <el-table-column prop="recommend" label="推荐量" width="90" sortable="custom" />
            <el-table-column prop="completed" label="成功推荐" width="100" sortable="custom" />
            <el-table-column prop="success_rate" label="成功率(%)" width="110" sortable="custom">
              <template #default="{ row }">
                <span :style="successRateStyle(row.success_rate)">{{ formatRate(row.success_rate) }}</span>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="tableData.length > 0"
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="sortedData.length"
            layout="total, sizes, prev, pager, next, jumper"
            style="margin-top: 15px; justify-content: flex-end"
          />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { api, useUserStore } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage } from 'element-plus'
import Echart from '../components/Echart.vue'
import { createPieOptions } from '../utils/echarts'
import { buildScatterOptions } from '../utils/broadbandScatter'
import { downloadBlob } from '../utils/download'
import { usePersistedFilters } from '../composables/usePersistedFilters'

const userStore = useUserStore()
const ui = useUiConfigStore()
const pageTitle = computed(() => ui.labels.broadband_report)

const now = new Date()
const defaultMonth = now.toISOString().slice(0, 7)

const { filters: searchForm, resetFilters: resetAllFilters } = usePersistedFilters(
  'broadband-report-filters',
  {
    type: 'month',
    date: '',
    month: defaultMonth,
    start_date: '',
    end_date: '',
    name: '',
    emp_no: '',
    team: '',
    class_name: '',
    city: ''
  }
)

const stats = reactive({
  total_people: 0,
  total_recommend: 0,
  total_completed: 0,
  avg_success_rate: 0,
  teams: [],
  classes: [],
  cities: []
})
const tableData = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const sortBy = ref('')
const sortOrder = ref('')
const filterType = ref('')
const filterValue = ref('')

const filteredData = computed(() => {
  let data = tableData.value
  if (filterType.value === 'team' && filterValue.value) {
    data = data.filter(d => d.team === filterValue.value)
  }
  return data
})

const sortedData = computed(() => {
  let data = [...filteredData.value]
  if (sortBy.value && sortOrder.value) {
    data.sort((a, b) => {
      let aVal = a[sortBy.value]
      let bVal = b[sortBy.value]
      if (sortBy.value === 'name' || sortBy.value === 'team') {
        return sortOrder.value === 'ascending'
          ? String(aVal || '').localeCompare(String(bVal || ''))
          : String(bVal || '').localeCompare(String(aVal || ''))
      }
      aVal = aVal ?? 0
      bVal = bVal ?? 0
      return sortOrder.value === 'ascending' ? aVal - bVal : bVal - aVal
    })
  }
  return data
})

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return sortedData.value.slice(start, start + pageSize.value)
})

const avgSuccessRate = computed(() => +(stats.avg_success_rate * 100).toFixed(2))

function formatRate(val) {
  if (val === null || val === undefined) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  if (isNaN(num)) return '-'
  return (num * 100).toFixed(2) + '%'
}

function successRateStyle(rate) {
  const pct = (rate ?? 0)
  if (pct >= 0.6) return { color: '#67C23A', fontWeight: 'bold' }
  if (pct >= 0.4) return { color: '#E6A23C', fontWeight: 'bold' }
  return { color: '#F56C6C' }
}

const teamChartData = computed(() => {
  const map = {}
  tableData.value.forEach(d => {
    const team = d.team || '未知班组'
    if (!map[team]) map[team] = { total: 0, completed: 0, people: new Set() }
    map[team].total += d.recommend
    map[team].completed += d.completed
    map[team].people.add(d.name)
  })
  return Object.entries(map)
    .map(([team, v]) => ({
      name: team,
      value: v.total,
      peopleCount: v.people.size,
      successRate: v.total > 0 ? v.completed / v.total : 0
    }))
    .sort((a, b) => b.value - a.value)
})

const teamChartOptions = computed(() => {
  const data = teamChartData.value
  if (!data.length) return {}
  return createPieOptions(
    data.map(d => ({ ...d, successRate: undefined })),
    '班组推荐量占比',
    undefined,
    '推荐量'
  )
})

const scatterFocus = ref(false)
const scatterHeight = computed(() => (scatterFocus.value ? 'calc(100vh - 240px)' : '480px'))

function toggleScatterFocus(params) {
  if (params && params.componentType === 'legend') return
  scatterFocus.value = !scatterFocus.value
}

const scatterOptions = computed(() => buildScatterOptions(filteredData.value, { showTitle: !scatterFocus.value }))

function handlePieClick(params) {
  if (!params || !params.name) return
  const team = params.name
  if (searchForm.team === team) {
    // 再点同一班组：取消筛选，回到全部
    searchForm.team = ''
    filterType.value = ''
    filterValue.value = ''
  } else {
    searchForm.team = team
    filterType.value = 'team'
    filterValue.value = team
  }
  currentPage.value = 1
}

function handleSortChange({ prop, order }) {
  sortBy.value = prop || ''
  sortOrder.value = order || ''
  currentPage.value = 1
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
    if (searchForm.emp_no) params.emp_no = searchForm.emp_no
    if (searchForm.team) params.team = searchForm.team
    if (searchForm.class_name) params.team_prefix = searchForm.class_name
    if (searchForm.city) params.city = searchForm.city
    const res = await api.get('/broadband/report', { params })
    Object.assign(stats, res.data.stats)
    tableData.value = res.data.items
    currentPage.value = 1
    filterType.value = ''
    filterValue.value = ''
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

function resetFilters() {
  resetAllFilters()
  loadData()
}

function handleExport() {
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
  if (searchForm.emp_no) params.emp_no = searchForm.emp_no
  if (searchForm.team) params.team = searchForm.team
  if (searchForm.class_name) params.team_prefix = searchForm.class_name
  if (searchForm.city) params.city = searchForm.city
  downloadBlob('/broadband/report/export', params, 'broadband_report.csv')
}

watch(() => searchForm.team, (val) => {
  if (val) searchForm.class_name = ''
  loadData()
})
watch(() => searchForm.class_name, (val) => {
  if (val) searchForm.team = ''
  loadData()
})

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stats-row {
  margin-bottom: 16px;
}
.scatter-wrap {
  position: relative;
}
.stats-overlay {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  z-index: 10;
  display: flex;
  justify-content: space-around;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #ebeef5;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
</style>