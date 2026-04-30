<template>
  <div class="users">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="handleAdd">新增用户</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="搜索">
          <el-input v-model="searchForm.search" placeholder="用户名/显示名" clearable />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="searchForm.role" placeholder="请选择" clearable>
            <el-option label="管理员" value="admin" />
            <el-option label="经理" value="manager" />
            <el-option label="普通用户" value="user" />
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
            <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'manager' ? 'warning' : 'success'">
              {{ row.role === 'admin' ? '管理员' : row.role === 'manager' ? '经理' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="权限" width="200">
          <template #default="{ row }">
            <el-tag v-if="row.role === 'admin'" type="danger">全部</el-tag>
            <template v-else>
              <el-tag v-for="(val, key) in parsePermissions(row.permissions)" :key="key" size="small" style="margin-right: 4px">
                {{ permLabel(key) }}
              </el-tag>
              <span v-if="!row.permissions || Object.keys(parsePermissions(row.permissions)).length === 0">无</span>
            </template>
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
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="warning" link @click="handleResetPwd(row)">重置密码</el-button>
            <el-button type="danger" link @click="handleDelete(row)">禁用</el-button>
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
          <el-select v-model="form.role" @change="handleRoleChange">
            <el-option label="普通用户" value="user" />
            <el-option label="经理" value="manager" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.role !== 'admin'" label="权限">
          <el-checkbox-group v-model="form.permissions">
            <el-checkbox label="upload_employee">上传员工</el-checkbox>
            <el-checkbox label="upload_schedule">上传排班</el-checkbox>
            <el-checkbox label="upload_checkin">上传签到</el-checkbox>
            <el-checkbox label="clear_data">清除数据</el-checkbox>
          </el-checkbox-group>
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
import { ElMessage, ElMessageBox } from 'element-plus'

const tableData = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const searchForm = reactive({ search: '', role: '' })
const form = reactive({ id: null, username: '', password: '', display_name: '', role: 'user', permissions: [] })
const pagination = reactive({ page: 1, limit: 20, total: 0 })

const permLabels = {
  upload_employee: '上传员工',
  upload_schedule: '上传排班',
  upload_checkin: '上传签到',
  clear_data: '清除数据'
}

function parsePermissions(permissions) {
  try {
    return JSON.parse(permissions || '{}')
  } catch {
    return {}
  }
}

function permLabel(key) {
  return permLabels[key] || key
}

function handleRoleChange(role) {
  if (role === 'admin') {
    form.permissions = []
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
  Object.assign(form, { id: null, username: '', password: '', display_name: '', role: 'user', permissions: [] })
  isEdit.value = false
  dialogVisible.value = true
}

function handleEdit(row) {
  const perms = parsePermissions(row.permissions)
  const permKeys = Object.keys(perms).filter(k => perms[k] === true)
  Object.assign(form, { id: row.id, username: row.username, display_name: row.display_name, role: row.role, permissions: permKeys })
  isEdit.value = true
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    const permObj = {}
    if (form.role !== 'admin') {
      form.permissions.forEach(p => { permObj[p] = true })
    }
    if (isEdit.value) {
      await api.put(`/users/${form.id}`, { display_name: form.display_name, role: form.role, permissions: JSON.stringify(permObj) })
      ElMessage.success('更新成功')
    } else {
      await api.post('/users', { ...form, permissions: JSON.stringify(permObj) })
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