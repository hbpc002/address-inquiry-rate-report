<template>
  <div class="users">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button v-if="userStore.hasPermission('users.manage')" type="primary" @click="handleAdd">新增用户</el-button>
          <el-button v-if="userStore.hasPermission('users.manage')" type="success" @click="importVisible = true">批量导入</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="搜索">
          <el-input v-model="searchForm.search" placeholder="用户名/显示名" clearable />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="searchForm.role" placeholder="请选择" clearable>
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.name" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>

       <el-table :data="tableData" border stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="display_name" label="显示名" width="120" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_system ? 'danger' : row.role === 'manager' ? 'warning' : 'success'">
              {{ row.role === 'admin' ? '管理员' : row.role === 'manager' ? '经理' : row.role }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '正常' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ row.created_at?.slice(0, 19) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('users.manage')" type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="userStore.hasPermission('users.manage')" type="warning" link @click="handleResetPwd(row)">重置密码</el-button>
            <el-button v-if="userStore.hasPermission('users.manage') && row.is_active" type="danger" link @click="handleDelete(row)">禁用</el-button>
            <el-button v-if="userStore.hasPermission('users.manage') && !row.is_active" type="success" link @click="handleEnable(row)">启用</el-button>
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

    <el-dialog v-model="importVisible" title="批量导入用户" width="500px">
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleFileChange"
        :file-list="importFileList"
      >
        <el-button type="primary">选择Excel文件</el-button>
        <template #tip>
          <div class="el-upload__tip">
            请上传 .xlsx 文件，<el-link type="primary" :underline="false" @click="handleDownloadTemplate">下载模板</el-link>
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_id" placeholder="选择角色" @change="handleRoleChange">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" :disabled="r.is_system && !userStore.isSystem">
              {{ r.name }}{{ r.is_system ? '（系统）' : '' }}
            </el-option>
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
const roles = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const searchForm = reactive({ search: '', role: '' })
const form = reactive({ id: null, username: '', password: '', display_name: '', role_id: null })
const pagination = reactive({ page: 1, limit: 20, total: 0 })

const importVisible = ref(false)
const importing = ref(false)
const uploadRef = ref(null)
const importFileList = ref([])
let importFile = null

function handleFileChange(file) {
  importFile = file.raw
}

async function handleImport() {
  if (!importFile) {
    ElMessage.warning('请先选择文件')
    return
  }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile)
    const res = await api.post('/users/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    const data = res.data
    let msg = `导入完成！新增${data.created}人`
    if (data.skipped > 0) msg += `，跳过${data.skipped}人`
    if (data.errors && data.errors.length > 0) {
      msg += `\n${data.errors.slice(0, 5).join('\n')}`
      if (data.errors.length > 5) msg += `\n...等${data.errors.length}条错误`
    }
    ElMessage.success(msg)
    importVisible.value = false
    importFile = null
    importFileList.value = []
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

async function handleDownloadTemplate() {
  try {
    const res = await api.get('/users/import-template', { responseType: 'blob' })
    const disposition = res.headers?.['content-disposition'] || ''
    const match = disposition.match(/filename\*?=(?:UTF-8'')?([^;\s]+)/i)
    const filename = match ? decodeURIComponent(match[1]) : '用户导入模板.xlsx'
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
      try { ElMessage.error(JSON.parse(text).detail || '下载模板失败') } catch { ElMessage.error(text || '下载模板失败') }
    } else {
      ElMessage.error('下载模板失败')
    }
  }
}

function handleRoleChange(roleId) {
}

async function loadRoles() {
  try {
    const res = await api.get('/users/roles')
    roles.value = res.data
  } catch (e) {
    console.error('Load roles failed', e)
  }
}

async function loadData() {
  try {
    const params = { page: pagination.page, limit: pagination.limit, ...searchForm }
    const res = await api.get('/users', { params })
    tableData.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

function handleAdd() {
  Object.assign(form, { id: null, username: '', password: '', display_name: '', role_id: null })
  isEdit.value = false
  dialogVisible.value = true
}

function handleEdit(row) {
  Object.assign(form, { id: row.id, username: row.username, display_name: row.display_name, role_id: row.role_id })
  isEdit.value = true
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    if (isEdit.value) {
      await api.put(`/users/${form.id}`, { display_name: form.display_name, role_id: form.role_id })
      ElMessage.success('更新成功')
    } else {
      await api.post('/users', { username: form.username, password: form.password, display_name: form.display_name, role_id: form.role_id })
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
    await ElMessageBox.confirm('确定要禁用该用户吗?', '提示', { type: 'warning' })
    await api.delete(`/users/${row.id}`)
    ElMessage.success('禁用成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}
async function handleEnable(row) {
  try {
    await ElMessageBox.confirm('确定要启用该用户吗?', '提示', { type: 'info' })
    await api.post(`/users/${row.id}/enable`)
    ElMessage.success('启用成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

async function handleResetPwd(row) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新密码', '重置密码', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPattern: /.+/,
      inputErrorMessage: '密码不能为空'
    })
    await api.post(`/users/${row.id}/reset-password`, { new_password: value })
    ElMessage.success('密码重置成功')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

function resetForm() {
  searchForm.search = ''
  searchForm.role = ''
  loadData()
}

onMounted(() => {
  loadRoles()
  loadData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>