<template>
  <div class="training-records">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.training_records }}</span>
          <el-space>
            <el-button v-if="userStore.hasPermission('training_records.view')" @click="loadData">刷新</el-button>
            <el-button
              v-if="userStore.hasPermission('training_records.delete')"
              type="danger"
              :disabled="!selectedIds.length"
              @click="handleBatchDelete"
            >批量删除</el-button>
            <el-button
              v-if="userStore.hasPermission('training_records.delete')"
              type="danger"
              plain
              @click="openCleanupDialog"
            >按天/月/批次删除</el-button>
            <el-button v-if="userStore.hasPermission('training_records.create')" type="primary" @click="openBatchDialog">批量录入</el-button>
            <el-button v-if="userStore.hasPermission('training_records.create')" type="success" @click="importVisible = true">导入培训记录</el-button>
          </el-space>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="日期范围">
          <el-date-picker v-model="searchForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" clearable style="width:140px" />
          <span style="margin: 0 8px">至</span>
          <el-date-picker v-model="searchForm.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" clearable style="width:140px" />
        </el-form-item>
        <el-form-item label="员工">
          <el-select v-model="searchForm.emp_no" filterable clearable placeholder="选择员工" style="width:160px">
            <el-option v-for="e in empOptions" :key="e.emp_no" :label="`${e.name} (${e.emp_no})`" :value="e.emp_no" />
          </el-select>
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="searchForm.team" filterable clearable placeholder="全部班组" style="width:140px">
            <el-option v-for="t in teams" :key="t.team" :label="`${t.team} (${t.count})`" :value="t.team" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="searchForm.type" clearable placeholder="全部" style="width:100px">
            <el-option label="培训" value="培训" />
            <el-option label="请假" value="请假" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <div v-if="stats.total > 0" style="margin-bottom: 12px">
        <el-tag type="info">共 {{ stats.total }} 条记录</el-tag>
        <el-tag type="warning" style="margin-left: 8px">总时长: {{ stats.total_minutes }} 分钟 ({{ (stats.total_minutes / 60).toFixed(1) }}h)</el-tag>
      </div>

      <el-table
        ref="tableRef"
        :data="tableData"
        row-key="id"
        border
        stripe
        max-height="calc(100vh - 320px)"
        @selection-change="handleSelectionChange"
      >
        <el-table-column v-if="userStore.hasPermission('training_records.delete')" type="selection" width="45" />
        <el-table-column prop="emp_no" label="工号" width="90" />
        <el-table-column prop="name" label="姓名" width="90" />
        <el-table-column prop="team" label="班组" width="120" show-overflow-tooltip />
        <el-table-column prop="record_date" label="日期" width="100" />
        <el-table-column label="起止时间" width="130">
          <template #default="{ row }">
            {{ row.start_time }} - {{ row.end_time }}
          </template>
        </el-table-column>
        <el-table-column prop="duration_minutes" label="时长(分钟)" width="90" sortable />
        <el-table-column prop="type" label="类型" width="70">
          <template #default="{ row }">
            <el-tag :type="row.type === '培训' ? 'primary' : 'warning'" size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="批次" width="90">
          <template #default="{ row }">
            {{ row.import_batch || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_by" label="录入人" width="80" />
        <el-table-column prop="created_at" label="录入时间" width="160">
          <template #default="{ row }">
            {{ row.created_at?.slice(0, 19) }}
          </template>
        </el-table-column>
        <el-table-column v-if="userStore.hasPermission('training_records.delete')" label="操作" width="60" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.limit"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadData"
        @size-change="handleSizeChange"
      />
    </el-card>

    <el-dialog v-model="batchDialogVisible" title="批量录入培训/请假" width="650px">
      <el-form :model="batchForm" label-width="100px">
        <el-form-item label="选择员工" required>
          <el-select v-model="batchForm.selectedEmps" multiple filterable placeholder="请选择员工" style="width: 100%">
            <el-option v-for="e in empOptions" :key="e.emp_no" :label="`${e.name} (${e.emp_no} - ${e.team})`" :value="e.emp_no" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择日期" required>
          <el-date-picker v-model="batchForm.dates" type="dates" value-format="YYYY-MM-DD" multiple placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="开始时间" required>
          <el-time-picker v-model="batchForm.startTime" format="HH:mm" value-format="HH:mm" placeholder="选择开始时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" required>
          <el-time-picker v-model="batchForm.endTime" format="HH:mm" value-format="HH:mm" placeholder="选择结束时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="batchForm.type" style="width: 100%">
            <el-option label="培训" value="培训" />
            <el-option label="请假" value="请假" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="batchForm.reason" type="textarea" :rows="2" placeholder="请输入原因/备注" />
        </el-form-item>
      </el-form>
      <div style="font-size: 12px; color: #909399; margin-top: -8px; margin-bottom: 8px;">
        将创建 {{ batchForm.selectedEmps.length * batchForm.dates.length }} 条记录
      </div>
       <template #footer>
         <el-button @click="batchDialogVisible = false">取消</el-button>
         <el-button type="primary" :loading="submitting" @click="handleBatchCreate" :disabled="!canSubmit">确认录入</el-button>
       </template>
     </el-dialog>

     <el-dialog v-model="importVisible" title="导入培训记录" width="500px">
       <el-upload
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        accept=".xlsx"
        :show-file-list="true"
        :file-list="importFileList"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽 xlsx 文件到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xlsx 格式，取最后一个工作表导入</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport" :disabled="!importFile">确认导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cleanupVisible" title="按天/按月/按批次删除" width="480px">
      <el-form label-width="90px">
        <el-form-item label="删除方式">
          <el-radio-group v-model="cleanupForm.mode">
            <el-radio-button value="date">按天</el-radio-button>
            <el-radio-button value="month">按月</el-radio-button>
            <el-radio-button value="batch">按批次</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="cleanupForm.mode === 'date'" label="选择日期">
          <el-date-picker v-model="cleanupForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item v-else-if="cleanupForm.mode === 'month'" label="选择月份">
          <el-date-picker v-model="cleanupForm.month" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width: 100%" />
        </el-form-item>
        <el-form-item v-else label="选择批次">
          <el-select v-model="cleanupForm.batch" filterable clearable placeholder="选择批次" style="width: 100%">
            <el-option v-for="b in batches" :key="b.batch" :label="batchLabel(b)" :value="b.batch" />
          </el-select>
        </el-form-item>
      </el-form>
      <div class="cleanup-tip">删除后不可恢复，请谨慎操作。</div>
      <template #footer>
        <el-button @click="cleanupVisible = false">取消</el-button>
        <el-button type="danger" :loading="cleanupLoading" :disabled="!canCleanup" @click="handleCleanupDelete">确认删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api, useUserStore } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

const userStore = useUserStore()
const ui = useUiConfigStore()

const empOptions = ref([])
const teams = ref([])
const batches = ref([])
const tableRef = ref(null)
const cleanupVisible = ref(false)
const cleanupLoading = ref(false)
const selectedIds = ref([])
const tableData = ref([])
const stats = reactive({ total: 0, total_minutes: 0 })
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const batchDialogVisible = ref(false)
const submitting = ref(false)
const importVisible = ref(false)
const importing = ref(false)
const importFile = ref(null)
const importFileList = ref([])

const searchForm = reactive({
  start_date: '',
  end_date: '',
  emp_no: '',
  team: '',
  type: ''
})

const batchForm = reactive({
  selectedEmps: [],
  dates: [],
  startTime: '',
  endTime: '',
  type: '培训',
  reason: ''
})

const cleanupForm = reactive({
  mode: 'date',
  date: '',
  month: '',
  batch: ''
})

const canSubmit = computed(() => {
  return batchForm.selectedEmps.length > 0
    && batchForm.dates.length > 0
    && batchForm.startTime
    && batchForm.endTime
})

const canCleanup = computed(() => {
  if (cleanupForm.mode === 'date') return Boolean(cleanupForm.date)
  if (cleanupForm.mode === 'month') return Boolean(cleanupForm.month)
  return Boolean(cleanupForm.batch)
})

async function loadEmployees() {
  try {
    const res = await api.get('/employees', { params: { limit: 1000, status: '在职', scope: 'legacy' } })
    empOptions.value = res.data.items || []
  } catch (e) {
    console.error(e)
  }
}

async function loadTeams() {
  try {
    const res = await api.get('/training-records/teams')
    teams.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

async function loadBatches() {
  try {
    const res = await api.get('/training-records/batches')
    batches.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

function batchLabel(b) {
  const reason = b.reason ? ` · ${b.reason}` : ''
  const createdAt = b.created_at ? ` · ${b.created_at.slice(0, 16).replace('T', ' ')}` : ''
  return `${b.batch}${reason} · ${b.count}条${createdAt}`
}

function openCleanupDialog() {
  cleanupForm.mode = 'date'
  cleanupForm.date = ''
  cleanupForm.month = ''
  cleanupForm.batch = ''
  cleanupVisible.value = true
  loadBatches()
}

async function loadData() {
  try {
    const params = {
      page: pagination.page,
      limit: pagination.limit
    }
    if (searchForm.start_date) params.start_date = searchForm.start_date
    if (searchForm.end_date) params.end_date = searchForm.end_date
    if (searchForm.emp_no) params.emp_no = searchForm.emp_no
    if (searchForm.team) params.team = searchForm.team
    if (searchForm.type) params.type = searchForm.type
    const res = await api.get('/training-records', { params })
    tableData.value = res.data.items || []
    tableRef.value?.clearSelection()
    selectedIds.value = []
    pagination.total = res.data.total
    stats.total = res.data.total
    stats.total_minutes = res.data.total_minutes
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

function handleSizeChange() {
  pagination.page = 1
  loadData()
}

function resetSearch() {
  searchForm.start_date = ''
  searchForm.end_date = ''
  searchForm.emp_no = ''
  searchForm.team = ''
  searchForm.type = ''
  pagination.page = 1
  loadData()
}

function handleSelectionChange(rows) {
  selectedIds.value = rows.map(r => r.id)
}

async function handleBatchDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedIds.value.length} 条记录？此操作不可恢复。`,
      '确认批量删除',
      { type: 'warning' }
    )
    const res = await api.post('/training-records/batch-delete', { ids: selectedIds.value })
    ElMessage.success(res.data.message || '删除成功')
    tableRef.value?.clearSelection()
    selectedIds.value = []
    loadData()
    loadTeams()
    loadBatches()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

async function handleCleanupDelete() {
  if (!canCleanup.value) return
  let target = ''
  if (cleanupForm.mode === 'date') target = `日期 ${cleanupForm.date}`
  else if (cleanupForm.mode === 'month') target = `月份 ${cleanupForm.month}`
  else target = `批次 ${cleanupForm.batch}`
  try {
    await ElMessageBox.confirm(
      `确定删除${target}的全部培训记录？此操作不可恢复。`,
      '确认删除',
      { type: 'warning' }
    )
    cleanupLoading.value = true
    let res
    if (cleanupForm.mode === 'date') {
      res = await api.delete('/training-records/by-date', { params: { date: cleanupForm.date } })
    } else if (cleanupForm.mode === 'month') {
      res = await api.delete('/training-records/by-month', { params: { year_month: cleanupForm.month } })
    } else {
      res = await api.delete(`/training-records/import/${encodeURIComponent(cleanupForm.batch)}`)
    }
    ElMessage.success(res.data.message || '删除成功')
    cleanupVisible.value = false
    pagination.page = 1
    loadData()
    loadTeams()
    loadBatches()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  } finally {
    cleanupLoading.value = false
  }
}

function openBatchDialog() {
  batchForm.selectedEmps = []
  batchForm.dates = []
  batchForm.startTime = ''
  batchForm.endTime = ''
  batchForm.type = '培训'
  batchForm.reason = ''
  batchDialogVisible.value = true
}

async function handleBatchCreate() {
  if (!canSubmit.value) {
    ElMessage.warning('请填写完整信息')
    return
  }
  submitting.value = true
  try {
    const records = []
    for (const empNo of batchForm.selectedEmps) {
      for (const d of batchForm.dates) {
        records.push({
          emp_no: empNo,
          record_date: d,
          start_time: batchForm.startTime,
          end_time: batchForm.endTime,
          type: batchForm.type,
          reason: batchForm.reason || ''
        })
      }
    }
    await api.post('/training-records/batch', { records })
    ElMessage.success(`成功录入 ${records.length} 条记录`)
    batchDialogVisible.value = false
    loadData()
    loadTeams()
    loadBatches()
  } catch (e) {
    ElMessage.error('录入失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除 ${row.emp_no} ${row.record_date} 的记录？`, '确认删除')
    await api.delete(`/training-records/${row.id}`)
    ElMessage.success('删除成功')
    if (tableData.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }
    loadData()
    loadTeams()
    loadBatches()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

function handleFileChange(file) {
  const isXlsx = file.name.endsWith('.xlsx')
  if (!isXlsx) {
    ElMessage.warning('请上传 .xlsx 格式的文件')
    importFileList.value = []
    return false
  }
  importFile.value = file.raw
  importFileList.value = [file]
  return false
}

async function handleImport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  importing.value = true
  const formData = new FormData()
  formData.append('file', importFile.value)
  try {
    const res = await api.post('/training-records/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success(res.data.message)
    importVisible.value = false
    importFile.value = null
    importFileList.value = []
    loadData()
    loadTeams()
    loadBatches()
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    ElMessage.error('导入失败: ' + detail)
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  loadEmployees()
  loadTeams()
  loadBatches()
  loadData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cleanup-tip {
  font-size: 12px;
  color: #f56c6c;
}
</style>
