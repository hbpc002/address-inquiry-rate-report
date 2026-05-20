<template>
  <div class="schedules">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>排班管理</span>
          <el-space>
            <el-button v-if="userStore.hasPermission('upload_schedule')" type="success" @click="dialogType = 'import'; importVisible = true">导入排班</el-button>
            <el-button type="primary" @click="dialogType = 'add'; dialogVisible = true">新增排班</el-button>
            <el-button type="warning" @click="dialogType = 'batch'; dialogVisible = true">批量排班</el-button>
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
            <el-option label="公休" value="公休" />
            <el-option label="加班" value="加班" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" border stripe>
        <el-table-column prop="schedule_date" label="日期" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="emp_no" label="工号" width="120" />
        <el-table-column prop="team" label="班组" width="100" />
        <el-table-column label="班次" width="180">
          <template #default="{ row }">
            <span v-if="row.shift_name">{{ row.shift_name }}</span>
            <span v-if="row.shift_time" style="color: #909399; margin-left: 4px">({{ row.shift_time }})</span>
            <span v-if="!row.shift_name && !row.shift_time">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时" width="60" />
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
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
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

    <!-- 导入排班对话框 -->
    <el-dialog v-if="userStore.hasPermission('upload_schedule')" v-model="importVisible" title="导入排班" width="500px">
      <el-upload
        ref="upload"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx"
        :on-change="handleFileChange"
      >
        <el-button type="primary">选择排班Excel文件</el-button>
        <template #tip>
          <div class="el-upload__tip">
            请上传排班表Excel文件，系统将自动解析员工信息和排班数据<br/>
            格式要求：第1列班组/角色，第2列姓名，后续列为日期和班次
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
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
            <el-option label="公休" value="公休" />
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
const importFile = ref(null)

async function loadData() {
  try {
    const params = { page: pagination.page, limit: pagination.limit }
    if (searchForm.date) params.schedule_date = searchForm.date
    if (searchForm.name) params.name = searchForm.name
    if (searchForm.emp_no) params.emp_no = searchForm.emp_no
    if (searchForm.team) params.team = searchForm.team
    if (searchForm.shift_type_id) params.shift_type_id = searchForm.shift_type_id
    if (searchForm.schedule_type) params.schedule_type = searchForm.schedule_type
    const res = await api.get('/schedules', { params })
    tableData.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    ElMessage.error('加载失败')
  }
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

function handleFileChange(file) {
  importFile.value = file.raw
}

async function handleImport() {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    const res = await api.post('/schedules/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success(`导入成功！新增员工${res.data.employees}人，排班${res.data.schedules}条`)
    importVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    uploading.value = false
  }
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