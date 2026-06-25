<template>
  <div class="schedules">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>排班管理</span>
          <el-space>
            <el-button v-if="userStore.hasPermission('schedules.upload')" type="success" @click="dialogType = 'import'; importVisible = true">导入考勤报表</el-button>
            <el-button v-if="userStore.hasPermission('schedules.create')" type="primary" @click="dialogType = 'add'; dialogVisible = true">新增排班</el-button>
            <el-button v-if="userStore.hasPermission('schedules.create')" type="warning" @click="dialogType = 'batch'; dialogVisible = true">批量排班</el-button>
          </el-space>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="日期">
          <el-date-picker v-model="searchForm.date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="请输入姓名" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="searchForm.emp_no" placeholder="请输入工号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="searchForm.team" placeholder="全部" clearable style="width: 110px">
            <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
          </el-select>
        </el-form-item>
        <el-form-item label="班次">
          <el-select v-model="searchForm.shift_type_id" placeholder="全部" clearable style="width: 110px">
            <el-option v-for="s in shiftTypes" :key="s.id" :label="s.shift_name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="searchForm.schedule_type" placeholder="全部" clearable style="width: 100px">
            <el-option label="正常" value="正常" />
            <el-option label="请假" value="请假" />
            <el-option label="休息" value="休息" />
            <el-option label="加班" value="加班" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <el-space style="margin-bottom: 12px">
        <el-button v-if="userStore.hasPermission('schedules.delete')" type="danger" :disabled="!selectedIds.length" @click="handleBatchDelete">
          批量删除 ({{ selectedIds.length }})
        </el-button>
      </el-space>
      <el-table :data="tableData" border stripe :row-class-name="segmentRowClass" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="40" :selectable="row => row._isFirst" />
        <el-table-column prop="schedule_date" label="日期" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="emp_no" label="工号" width="120" />
        <el-table-column prop="team" label="班组" width="100" />
        <el-table-column label="班次" width="220">
          <template #default="{ row }">
            <div v-if="row.shift_name">
              <span>{{ row.shift_name }}</span>
              <span style="color: #909399; margin-left: 4px">({{ row._displayShiftTime || row.shift_time }})</span>
              <el-tag v-if="row._totalSegments > 1" size="small" type="info" style="margin-left: 6px">
                {{ row._segmentIndex + 1 }}/{{ row._totalSegments }}
              </el-tag>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时" width="60" />
        <el-table-column label="遵时率" width="80">
          <template #default="{ row }">
            <span>{{ _segValue(row, 'punctuality_rate') }}</span>
          </template>
        </el-table-column>
        <el-table-column label="通话时长" width="80">
          <template #default="{ row }">
            <span>{{ _segValue(row, 'call_duration') }}</span>
          </template>
        </el-table-column>
        <el-table-column label="整理时长" width="80">
          <template #default="{ row }">
            <span>{{ _segValue(row, 'organize_duration') }}</span>
          </template>
        </el-table-column>
        <el-table-column label="工时利用率" width="80">
          <template #default="{ row }">
            <span>{{ _segValue(row, 'utilization_rate') }}</span>
          </template>
        </el-table-column>
        <el-table-column label="班表出勤率" width="90">
          <template #default="{ row }">
            <span>{{ _segValue(row, 'attendance_rate') }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="schedule_type" label="排班类型" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.schedule_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ row.created_at?.slice(0, 19) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <template v-if="row._isFirst">
              <el-button v-if="userStore.hasPermission('schedules.edit')" type="primary" link @click="handleEdit(row)">编辑</el-button>
              <el-button v-if="userStore.hasPermission('schedules.delete')" type="danger" link @click="handleDelete(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.limit"
        :total="pagination.total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </el-card>

    <!-- 导入考勤报表对话框 -->
    <el-dialog v-if="userStore.hasPermission('schedules.upload')" v-model="importVisible" title="导入考勤报表" width="500px" @closed="closeImport">
      <el-upload
        ref="upload"
        drag
        :auto-upload="false"
        multiple
        accept=".xlsx"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽Excel文件到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">支持多文件同时拖入，系统将自动解析排班、遵时率、通话时长、整理时长、工时利用率、班表出勤率<br/>
          格式：考勤出勤报表(.xlsx)，每行一个时段</div>
        </template>
      </el-upload>
      <div v-if="importResults.length" style="margin-top: 12px">
        <el-tag v-for="r in importResults" :key="r.file" :type="r.success ? 'success' : 'danger'" style="margin: 2px; white-space: normal; height: auto; line-height: 1.4; padding: 4px 8px">
          {{ r.file }} → {{ r.success ? `导入成功：员工${r.employees}人，排班${r.schedules}条` : r.error }}
        </el-tag>
      </div>
      <template #footer>
        <el-button @click="closeImport">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增排班' : dialogType === 'batch' ? '批量排班' : '编辑排班'" width="500px">
      <el-form v-if="dialogType === 'add'" :model="form" label-width="80px">
        <el-form-item label="员工">
          <el-select v-model="form.emp_id" placeholder="请选择员工" filterable>
            <el-option v-for="e in employees" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="form.schedule_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="班次">
          <el-select v-model="form.shift_type_id" placeholder="请选择班次">
            <el-option v-for="s in shiftTypes" :key="s.id" :label="s.shift_name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.schedule_type">
            <el-option label="正常" value="正常" />
            <el-option label="请假" value="请假" />
            <el-option label="休息" value="休息" />
            <el-option label="加班" value="加班" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-form v-else-if="dialogType === 'batch'" :model="batchForm" label-width="80px">
        <el-form-item label="员工">
          <el-select v-model="batchForm.emp_ids" multiple placeholder="请选择员工" filterable>
            <el-option v-for="e in employees" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="batchForm.schedule_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="班次">
          <el-select v-model="batchForm.shift_type_id" placeholder="请选择班次">
            <el-option v-for="s in shiftTypes" :key="s.id" :label="s.shift_name" :value="s.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../stores/user'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

const userStore = useUserStore()
const tableData = ref([])
const dialogVisible = ref(false)
const importVisible = ref(false)
const uploading = ref(false)
const dialogType = ref('add')
const teams = ref([])
const employees = ref([])
const shiftTypes = ref([])
const searchForm = reactive({ date: '', name: '', emp_no: '', team: '', shift_type_id: null, schedule_type: '' })
const form = reactive({ emp_id: null, schedule_date: '', shift_type_id: null, schedule_type: '正常', notes: '' })
const batchForm = reactive({ emp_ids: [], schedule_date: '', shift_type_id: null })
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const fileList = ref([])
const importResults = ref([])
const selectedIds = ref([])

async function loadData() {
  selectedIds.value = []
  try {
    const params = { page: pagination.page, limit: pagination.limit }
    if (searchForm.date) params.schedule_date = searchForm.date
    if (searchForm.name) params.name = searchForm.name
    if (searchForm.emp_no) params.emp_no = searchForm.emp_no
    if (searchForm.team) params.team = searchForm.team
    if (searchForm.shift_type_id) params.shift_type_id = searchForm.shift_type_id
    if (searchForm.schedule_type) params.schedule_type = searchForm.schedule_type
    const res = await api.get('/schedules', { params })
    // 展开多段班次为多行显示
    const expanded = []
    for (const item of res.data.items) {
      const segments = item.time_segments || []
      if (segments.length <= 1) {
        expanded.push({ ...item, _segmentIndex: 0, _totalSegments: 1, _isFirst: true, _displayShiftTime: item.shift_time })
      } else {
        segments.forEach((seg, i) => {
          expanded.push({
            ...item,
            _segmentIndex: i,
            _totalSegments: segments.length,
            _isFirst: i === 0,
            _displayShiftTime: `${seg.start}-${seg.end}`
          })
        })
      }
    }
    tableData.value = expanded
    pagination.total = res.data.total
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

function _segValue(row, field) {
  const seg = row.time_segments?.[row._segmentIndex]
  const val = seg?.[field] ?? row[field]
  if (val == null || val === '') return '-'
  if (['punctuality_rate', 'utilization_rate', 'attendance_rate'].includes(field)) {
    return Number(val).toFixed(1) + '%'
  }
  return Number(val).toFixed(2)
}

function segmentRowClass({ row }) {
  return row._segmentIndex > 0 ? 'segment-sub-row' : ''
}

function resetSearch() {
  searchForm.date = ''
  searchForm.name = ''
  searchForm.emp_no = ''
  searchForm.team = ''
  searchForm.shift_type_id = null
  searchForm.schedule_type = ''
  pagination.page = 1
  loadData()
}

async function loadOptions() {
  try {
    const [eRes, sRes, tRes] = await Promise.all([
      api.get('/employees', { params: { limit: 1000 } }),
      api.get('/shift-types'),
      api.get('/employees/teams')
    ])
    employees.value = eRes.data.items
    shiftTypes.value = sRes.data
    teams.value = tRes.data
  } catch (e) {
    console.error(e)
  }
}

function handleFileChange(file, files) {
  fileList.value = files.map(f => ({ name: f.name, raw: f.raw }))
}

function handleFileRemove(file, files) {
  fileList.value = files.map(f => ({ name: f.name, raw: f.raw }))
}

async function handleImport() {
  if (!fileList.value.length) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  importResults.value = []
  let successCount = 0
  let failCount = 0
  for (const f of fileList.value) {
    try {
      const formData = new FormData()
      formData.append('file', f.raw)
      const res = await api.post('/schedules/import-attendance-report', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      importResults.value.push({ file: f.name, success: true, employees: res.data.employees, schedules: res.data.schedules })
      successCount++
    } catch (e) {
      importResults.value.push({ file: f.name, success: false, error: e.response?.data?.detail || '导入失败' })
      failCount++
    }
  }
  uploading.value = false
  if (failCount === 0) {
    ElMessage.success(`全部导入成功，共${successCount}个文件`)
  } else {
    ElMessage.warning(`${successCount}个文件成功，${failCount}个文件失败`)
  }
  loadData()
}

function closeImport() {
  importVisible.value = false
  fileList.value = []
  importResults.value = []
}

function handleEdit(row) {
  Object.assign(form, { ...row })
  dialogType.value = 'add'
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    if (dialogType.value === 'add') {
      await api.post('/schedules', form)
      ElMessage.success('创建成功')
    } else {
      await api.post('/schedules/batch', batchForm)
      ElMessage.success('批量排班成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该排班吗?', '提示', { type: 'warning' })
    await api.delete(`/schedules/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function handleSelectionChange(rows) {
  const ids = new Set()
  for (const row of rows) {
    if (row._isFirst) {
      ids.add(row.id)
    }
  }
  selectedIds.value = [...ids]
}

async function handleBatchDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 条排班记录吗？`, '提示', { type: 'warning' })
    const res = await api.delete('/schedules/batch', { params: { ids: selectedIds.value } })
    ElMessage.success(res.data.message)
    selectedIds.value = []
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '批量删除失败')
    }
  }
}

onMounted(() => {
  loadData()
  loadOptions()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

<style>
.el-table .segment-sub-row td {
  background-color: #fafafa !important;
}
.el-table .segment-sub-row:hover td {
  background-color: #f0f9ff !important;
}
</style>