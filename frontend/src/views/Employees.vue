<template>
  <div class="employees">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>员工管理</span>
          <el-space>
            <template v-if="activeTab === 'active'">
              <el-button v-if="userStore.hasPermission('employees.export')" @click="handleExport">导出员工</el-button>
              <el-button v-if="userStore.hasPermission('employees.upload')" type="success" @click="importVisible = true">导入员工</el-button>
              <el-button v-if="userStore.hasPermission('employees.create')" type="primary" @click="handleAdd">新增员工</el-button>
            </template>
            <template v-else>
              <el-button v-if="userStore.hasPermission('employees.export')" @click="handleExport">导出员工</el-button>
              <el-button :disabled="!selectedIds.length" v-if="userStore.hasPermission('employees.restore')" type="primary" @click="handleBatchRestore">批量恢复</el-button>
              <el-button :disabled="!selectedIds.length" v-if="userStore.hasPermission('employees.delete')" type="danger" @click="handleBatchHardDelete">批量彻底删除</el-button>
            </template>
          </el-space>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="在职员工" name="active">
          <el-form inline>
            <el-form-item label="搜索">
              <el-input v-model="searchForm.search" placeholder="工号/姓名" clearable />
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchForm.team" placeholder="请选择" clearable style="width:160px">
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="searchForm.dept" placeholder="请选择" clearable style="width:160px">
                <el-option v-for="d in departments" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item label="岗位">
              <el-select v-model="searchForm.role" placeholder="请选择" clearable style="width:160px">
                <el-option v-for="r in roles" :key="r.role" :label="r.role" :value="r.role" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadData">查询</el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="tableData" border stripe>
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="120" />
            <el-table-column prop="dept" label="部门" width="120" />
            <el-table-column prop="role" label="岗位" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === '在职' ? 'success' : 'danger'">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ row.created_at?.slice(0, 19) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button v-if="userStore.hasPermission('employees.edit')" type="primary" link @click="handleEdit(row)">编辑</el-button>
                <el-button v-if="userStore.hasPermission('employees.delete')" type="danger" link @click="handleDelete(row)">删除</el-button>
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
        </el-tab-pane>

        <el-tab-pane label="回收站" name="recycle">
          <el-form inline>
            <el-form-item label="搜索">
              <el-input v-model="recycleSearch.search" placeholder="工号/姓名" clearable />
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="recycleSearch.team" placeholder="请选择" clearable style="width:160px">
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="recycleSearch.dept" placeholder="请选择" clearable style="width:160px">
                <el-option v-for="d in departments" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadData">查询</el-button>
              <el-button @click="resetRecycleSearch">重置</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="tableData" border stripe @selection-change="handleSelectionChange">
            <el-table-column type="selection" width="50" />
            <el-table-column prop="emp_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="120" />
            <el-table-column prop="dept" label="部门" width="120" />
            <el-table-column prop="role" label="岗位" width="80" />
            <el-table-column prop="deleted_at" label="删除时间" width="180">
              <template #default="{ row }">
                {{ row.deleted_at?.slice(0, 19) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button v-if="userStore.hasPermission('employees.restore')" type="primary" link @click="handleRestore(row)">恢复</el-button>
                <el-button v-if="userStore.hasPermission('employees.delete')" type="danger" link @click="handleHardDelete(row)">彻底删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="recyclePagination.page"
            v-model:page-size="recyclePagination.limit"
            :total="recyclePagination.total"
            layout="total, prev, pager, next"
            @current-change="loadData"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑员工' : '新增员工'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="工号">
          <el-input v-model="form.emp_no" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="班组">
          <el-input v-model="form.team" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.dept" />
        </el-form-item>
        <el-form-item label="岗位">
          <el-select v-model="form.role">
            <el-option label="组长" value="组长" />
            <el-option label="师傅" value="师傅" />
            <el-option label="组员" value="组员" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-if="userStore.hasPermission('employees.upload')" v-model="importVisible" title="导入员工" width="500px">
      <el-upload
        ref="upload"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx"
        :on-change="handleFileChange"
      >
        <el-button type="primary">选择员工Excel文件</el-button>
        <template #tip>
          <div class="el-upload__tip">
            请上传员工信息Excel文件，需包含以下列：工号、姓名<br/>
            可选列：班组、部门、岗位、状态
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleImport">导入</el-button>
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
const isEdit = ref(false)
const selectedIds = ref([])

const activeTab = ref('active')

const searchForm = reactive({ search: '', team: '', dept: '', role: '' })
const recycleSearch = reactive({ search: '', team: '', dept: '' })
const form = reactive({ emp_no: '', name: '', team: '', dept: '', role: '组员' })
const teams = ref([])
const departments = ref([])
const roles = ref([])
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const recyclePagination = reactive({ page: 1, limit: 20, total: 0 })
const importFile = ref(null)

function getStatusFilter() {
  return activeTab.value === 'active' ? '在职' : '离职'
}

function getPagination() {
  return activeTab.value === 'active' ? pagination : recyclePagination
}

async function loadData() {
  try {
    const p = getPagination()
    const search = activeTab.value === 'active' ? searchForm : recycleSearch
    const params = {
      page: p.page,
      limit: p.limit,
      status: getStatusFilter(),
      ...search
    }
    const res = await api.get('/employees', { params })
    tableData.value = res.data.items
    p.total = res.data.total
    selectedIds.value = []
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

async function loadFilters() {
  try {
    const [tRes, dRes, rRes] = await Promise.all([
      api.get('/employees/teams'),
      api.get('/checkins/departments'),
      api.get('/employees/roles')
    ])
    teams.value = tRes.data
    departments.value = dRes.data
    roles.value = rRes.data
  } catch (e) {
    console.error(e)
  }
}

function handleTabChange() {
  selectedIds.value = []
  loadData()
}

function handleAdd() {
  Object.assign(form, { emp_no: '', name: '', team: '', dept: '', role: '组员' })
  isEdit.value = false
  dialogVisible.value = true
}

async function handleExport() {
  try {
    const params = {}
    const search = activeTab.value === 'active' ? searchForm : recycleSearch
    if (search.team) params.team = search.team
    if (search.dept) params.dept = search.dept
    params.status = getStatusFilter()
    const res = await api.get('/employees/export', { params, responseType: 'blob' })
    const disposition = res.headers?.['content-disposition'] || ''
    const match = disposition.match(/filename\*?=(?:UTF-8'')?([^;\s]+)/i)
    const filename = match ? decodeURIComponent(match[1]) : 'employees.csv'
    const url = URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    const errData = e.response?.data
    if (errData instanceof Blob) {
      const text = await errData.text()
      try { ElMessage.error(JSON.parse(text).detail || '导出失败') } catch { ElMessage.error(text || '导出失败') }
    } else {
      ElMessage.error('导出失败')
    }
  }
}

function handleEdit(row) {
  Object.assign(form, { ...row })
  isEdit.value = true
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    if (isEdit.value) {
      await api.put(`/employees/${form.id}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/employees', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该员工吗?', '提示', { type: 'warning' })
    await api.delete(`/employees/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleRestore(row) {
  try {
    await ElMessageBox.confirm(`确定要恢复员工"${row.name}"(${row.emp_no})吗？`, '提示')
    await api.put(`/employees/${row.id}/restore`)
    ElMessage.success('恢复成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('恢复失败')
    }
  }
}

async function handleHardDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要彻底删除员工"${row.name}"(${row.emp_no})吗？\n该员工的排班记录和考勤报表数据将被一并删除，此操作不可恢复！`,
      '警告',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await api.delete(`/employees/${row.id}/hard-delete`)
    ElMessage.success('已彻底删除')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function handleSelectionChange(rows) {
  selectedIds.value = rows.map(r => r.id)
}

async function handleBatchRestore() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确定要恢复选中的 ${selectedIds.value.length} 名员工吗？`, '提示')
    await api.post('/employees/batch-restore', selectedIds.value)
    ElMessage.success('批量恢复成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('批量恢复失败')
    }
  }
}

async function handleBatchHardDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定要彻底删除选中的 ${selectedIds.value.length} 名员工吗？\n相关排班和考勤数据将被一并删除，此操作不可恢复！`,
      '警告',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await api.post('/employees/batch-hard-delete', selectedIds.value)
    ElMessage.success('批量彻底删除完成')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

function resetForm() {
  searchForm.search = ''
  searchForm.team = ''
  searchForm.dept = ''
  searchForm.role = ''
  loadData()
}

function resetRecycleSearch() {
  recycleSearch.search = ''
  recycleSearch.team = ''
  recycleSearch.dept = ''
  loadData()
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
    const res = await api.post('/employees/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success(`导入完成！新增${res.data.created}人，更新${res.data.updated}人`)
    importVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  loadData()
  loadFilters()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
