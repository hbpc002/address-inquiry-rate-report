<template>
  <div class="broadband-compare">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>下单/竣工口径对比</span>
          <span>
            <el-button size="small" @click="router.push('/broadband-report')">返回画像</el-button>
            <el-button v-if="userStore.hasPermission('broadband_report.export')" type="success" size="small" @click="handleExport">导出</el-button>
          </span>
        </div>
      </template>

      <el-alert
        title="推荐量按下单日期统计，成功推荐同时展示下单日期与竣工日期两种口径；跨期订单会造成两种口径存在差异。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
      />

      <el-form inline>
        <el-form-item label="查询方式">
          <el-radio-group v-model="searchForm.type">
            <el-radio value="day">按天</el-radio>
            <el-radio value="month">按月</el-radio>
            <el-radio value="range">自定义</el-radio>
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

      <el-row class="stats-row">
        <div class="stat-item">
          <el-statistic title="总人数" :value="stats.total_people" />
        </div>
        <div class="stat-item">
          <el-statistic title="推荐量(下单)" :value="stats.total_recommend" :precision="0" />
        </div>
        <div class="stat-item">
          <el-statistic title="成功推荐(下单)" :value="stats.total_completed_by_order" :precision="0" />
        </div>
        <div class="stat-item">
          <el-statistic title="成功推荐(竣工)" :value="stats.total_completed_by_finish" :precision="0" />
        </div>
        <div class="stat-item">
          <el-statistic title="口径差异" :value="stats.total_diff" :precision="0" />
        </div>
        <div class="stat-item">
          <el-statistic title="竣工口径成功率(%)" :value="finishSuccessRate" :precision="2" />
        </div>
      </el-row>

      <el-table :data="items" border stripe max-height="calc(100vh - 520px)">
        <el-table-column prop="emp_no" label="工号" width="120" />
        <el-table-column prop="name" label="姓名" width="90" />
        <el-table-column prop="team" label="班组" min-width="140" />
        <el-table-column prop="recommend" label="推荐量(下单)" width="120" />
        <el-table-column prop="completed_by_order" label="成功推荐(下单)" width="130" />
        <el-table-column prop="completed_by_finish" label="成功推荐(竣工)" width="130" />
        <el-table-column prop="diff" label="差异" width="80">
          <template #default="{ row }">
            <span :class="diffClass(row.diff)">{{ row.diff > 0 ? '+' : '' }}{{ row.diff }}</span>
          </template>
        </el-table-column>
        <el-table-column label="下单口径成功率" width="130">
          <template #default="{ row }">{{ formatRate(row.success_rate_by_order) }}</template>
        </el-table-column>
        <el-table-column label="竣工口径成功率" width="130">
          <template #default="{ row }">{{ formatRate(row.success_rate_by_finish) }}</template>
        </el-table-column>
        <el-table-column prop="points_by_order" label="下单口径积分" width="110" />
        <el-table-column prop="points_by_finish" label="竣工口径积分" width="110" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import { downloadBlob } from '../utils/download'
import { usePersistedFilters } from '../composables/usePersistedFilters'

const router = useRouter()
const userStore = useUserStore()
const now = new Date()
const defaultMonth = now.toISOString().slice(0, 7)

const { filters: searchForm, resetFilters: resetAllFilters } = usePersistedFilters(
  'broadband-compare-filters',
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
  total_completed_by_order: 0,
  total_completed_by_finish: 0,
  total_diff: 0,
  avg_success_rate_by_order: 0,
  avg_success_rate_by_finish: 0,
  teams: [],
  classes: [],
  cities: []
})
const items = ref([])

const finishSuccessRate = computed(() => +(stats.avg_success_rate_by_finish * 100).toFixed(2))

function formatRate(value) {
  if (value === null || value === undefined) return '-'
  const num = typeof value === 'number' ? value : parseFloat(value)
  if (isNaN(num)) return '-'
  return (num * 100).toFixed(2) + '%'
}

function diffClass(value) {
  if (value > 0) return 'diff-positive'
  if (value < 0) return 'diff-negative'
  return ''
}

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
  if (searchForm.name) params.name = searchForm.name
  if (searchForm.emp_no) params.emp_no = searchForm.emp_no
  if (searchForm.team) params.team = searchForm.team
  if (searchForm.class_name) params.team_prefix = searchForm.class_name
  if (searchForm.city) params.city = searchForm.city
  return params
}

async function loadData() {
  try {
    const res = await api.get('/broadband/report/compare', { params: buildParams() })
    Object.assign(stats, res.data.stats)
    items.value = res.data.items
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

function resetFilters() {
  resetAllFilters()
  loadData()
}

function handleExport() {
  downloadBlob('/broadband/report/compare/export', buildParams(), 'broadband_compare.csv')
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
.stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 16px;
}
.diff-positive {
  color: #67c23a;
  font-weight: bold;
}
.diff-negative {
  color: #f56c6c;
  font-weight: bold;
}
</style>
