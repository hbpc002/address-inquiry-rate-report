<template>
  <div class="employees">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>员工管理</span>
          <el-space>
            <el-button type="success" @click="importVisible = true">导入员工</el-button>
            <el-button type="primary" @click="handleAdd">新增员工</el-button>
          </el-space>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="搜索">
          <el-input v-model="searchForm.search" placeholder="工号/姓名" clearable />
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="searchForm.team" placeholder="请选择" clearable>
            <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="searchForm.dept" placeholder="请选择" clearable>
            <el-option v-for="d in departments" :key="d.dept" :label="d.dept" :value="d.dept" />
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

    <el-dialog v-model="importVisible" title="导入员工" width="500px">
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
import { ElMessage, ElMessageBox } from 'element-plus'

const tableData = ref([])
const dialogVisible = ref(false)
const importVisible = ref(false)
const uploading = ref(false)
const isEdit = ref(false)
const searchForm = reactive({ search: '', team: '', dept: '' })
const form = reactive({ emp_no: '', name: '', team: '', dept: '', role: '组员' })
const teams = ref([])
const departments = ref([])
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const importFile = ref(null)

async function loadData() {
  try {
    const params = {
      page: pagination.page,
      limit: pagination.limit,
      ...searchForm
    }
    const res = await api.get('/employees', { params })
    tableData.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

async function loadFilters() {
  try {
    const [tRes, dRes] = await Promise.all([api.get('/employees/teams'), api.get('/employees/departments')])
    teams.value = tRes.data
    departments.value = dRes.data
  } catch (e) {
    console.error(e)
  }
}

function handleAdd() {
  Object.assign(form, { emp_no: '', name: '', team: '', dept: '', role: '组员' })
  isEdit.value = false
  dialogVisible.value = true
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

function resetForm() {
  searchForm.search = ''
  searchForm.team = ''
  searchForm.dept = ''
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