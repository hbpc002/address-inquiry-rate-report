<template>
  <div class="roles">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>角色管理</span>
          <el-button v-if="userStore.hasPermission('roles.manage')" type="primary" @click="handleAdd">新增角色</el-button>
        </div>
      </template>

      <el-table :data="tableData" border stripe>
        <el-table-column prop="name" label="角色名称" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_system ? 'danger' : 'warning'">{{ row.name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" width="200" />
        <el-table-column label="权限" min-width="300">
          <template #default="{ row }">
            <el-tag v-if="row.is_system" type="danger">全部权限</el-tag>
            <template v-else>
              <el-tag
                v-for="item in getPermissionSummary(row.permissions)"
                :key="item.pageKey"
                size="small"
                style="margin: 2px; cursor: default"
                :type="item.enabled === 0 ? 'info' : item.enabled === item.total ? 'success' : 'warning'"
              >
                {{ item.label }} ({{ item.enabled }}/{{ item.total }})
              </el-tag>
              <span v-if="!row.permissions">无</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('roles.manage') && !row.is_system" type="primary" link @click="handleAssign(row)">分配人员</el-button>
            <el-button v-if="userStore.hasPermission('roles.manage') && !row.is_system" type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="userStore.hasPermission('roles.manage') && !row.is_system" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑角色' : '新增角色'" width="780px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="角色名称">
          <el-input v-model="form.name" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="权限">
          <div style="margin-bottom: 12px">
            <el-checkbox :indeterminate="isIndeterminate" :model-value="checkAll" @change="handleCheckAll">全选所有权限</el-checkbox>
          </div>
          <div v-for="(pageInfo, pageKey) in PERMISSION_REGISTRY" :key="pageKey" style="margin-bottom: 12px">
            <el-card shadow="hover" body-style="padding: 12px">
              <template #header>
                <div style="display: flex; align-items: center; justify-content: space-between">
                  <span style="font-weight: bold">{{ pageInfo.label }}</span>
                  <el-checkbox
                    :indeterminate="isGroupIndeterminate(pageKey)"
                    :model-value="isGroupAllChecked(pageKey)"
                    @change="val => handleGroupCheckAll(pageKey, val)"
                    size="small"
                  >全选</el-checkbox>
                </div>
              </template>
              <el-checkbox-group v-model="form.permissions">
                <el-checkbox
                  v-for="(label, action) in pageInfo.permissions"
                  :key="`${pageKey}.${action}`"
                  :label="`${pageKey}.${action}`"
                  size="small"
                >
                  {{ label }}
                </el-checkbox>
              </el-checkbox-group>
            </el-card>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="assignDialogVisible" :title="'分配人员 - ' + (assignRole?.name || '')" width="500px">
      <el-form label-width="80px">
        <el-form-item label="选择用户">
          <el-select
            v-model="assignUserIds"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="搜索并选择用户"
            style="width: 100%"
          >
            <el-option
              v-for="u in allUsers"
              :key="u.id"
              :label="u.display_name ? `${u.username} (${u.display_name})` : u.username"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="assignLoading" @click="handleAssignSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../stores/user'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PERMISSION_REGISTRY, getAllPermissionKeys } from '../permissions'

const userStore = useUserStore()

const tableData = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive({ id: null, name: '', description: '', permissions: [] })

const assignDialogVisible = ref(false)
const assignRole = ref(null)
const assignUserIds = ref([])
const allUsers = ref([])
const assignLoading = ref(false)

const allKeys = getAllPermissionKeys()
const checkAll = computed(() => form.permissions.length === allKeys.length)
const isIndeterminate = computed(() => form.permissions.length > 0 && form.permissions.length < allKeys.length)

function handleCheckAll(val) {
  form.permissions = val ? [...allKeys] : []
}

function parsePermissions(permissions) {
  try {
    const obj = JSON.parse(permissions || '{}')
    const sorted = {}
    for (const key of allKeys) {
      if (obj[key] === true) {
        sorted[key] = true
      }
    }
    return sorted
  } catch {
    return {}
  }
}

function getPermissionSummary(permissionsStr) {
  try {
    const obj = JSON.parse(permissionsStr || '{}')
    return Object.entries(PERMISSION_REGISTRY).map(([pageKey, pageInfo]) => {
      const actions = Object.keys(pageInfo.permissions)
      const enabledCount = actions.filter(a => obj[`${pageKey}.${a}`] === true).length
      return { pageKey, label: pageInfo.label, enabled: enabledCount, total: actions.length }
    })
  } catch {
    return []
  }
}

function getGroupKeys(pageKey) {
  const pageInfo = PERMISSION_REGISTRY[pageKey]
  if (!pageInfo) return []
  return Object.keys(pageInfo.permissions).map(a => `${pageKey}.${a}`)
}

function isGroupAllChecked(pageKey) {
  const groupKeys = getGroupKeys(pageKey)
  return groupKeys.length > 0 && groupKeys.every(k => form.permissions.includes(k))
}

function isGroupIndeterminate(pageKey) {
  const groupKeys = getGroupKeys(pageKey)
  const checkedCount = groupKeys.filter(k => form.permissions.includes(k)).length
  return checkedCount > 0 && checkedCount < groupKeys.length
}

function handleGroupCheckAll(pageKey, checked) {
  const groupKeys = getGroupKeys(pageKey)
  if (checked) {
    const toAdd = groupKeys.filter(k => !form.permissions.includes(k))
    form.permissions.push(...toAdd)
  } else {
    form.permissions = form.permissions.filter(k => !groupKeys.includes(k))
  }
}

async function loadData() {
  try {
    const res = await api.get('/roles/all')
    tableData.value = res.data
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

function handleAdd() {
  Object.assign(form, { id: null, name: '', description: '', permissions: [...allKeys] })
  isEdit.value = false
  dialogVisible.value = true
}

function handleEdit(row) {
  const perms = parsePermissions(row.permissions)
  Object.assign(form, {
    id: row.id,
    name: row.name,
    description: row.description,
    permissions: Object.keys(perms),
  })
  isEdit.value = true
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    const permObj = {}
    form.permissions.forEach(p => { permObj[p] = true })
    for (const key of allKeys) {
      if (!permObj[key]) permObj[key] = false
    }
    if (isEdit.value) {
      await api.put(`/roles/${form.id}`, { permissions: permObj, description: form.description })
      ElMessage.success('更新成功')
    } else {
      await api.post('/roles', { name: form.name, description: form.description, permissions: permObj })
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
    await ElMessageBox.confirm(`确定要删除角色"${row.name}"吗？`, '提示', { type: 'warning' })
    await api.delete(`/roles/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

async function loadAllUsers() {
  try {
    const res = await api.get('/roles/all-users')
    allUsers.value = res.data
  } catch (e) {
    ElMessage.error('加载用户列表失败')
  }
}

async function loadRoleUsers(roleId) {
  try {
    const res = await api.get(`/roles/${roleId}/users`)
    assignUserIds.value = res.data.map(u => u.id)
  } catch (e) {
    ElMessage.error('加载已分配用户失败')
  }
}

async function handleAssign(row) {
  assignRole.value = row
  assignUserIds.value = []
  assignDialogVisible.value = true
  await Promise.all([loadAllUsers(), loadRoleUsers(row.id)])
}

async function handleAssignSubmit() {
  assignLoading.value = true
  try {
    await api.put(`/roles/${assignRole.value.id}`, { user_ids: assignUserIds.value })
    ElMessage.success('分配成功')
    assignDialogVisible.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '分配失败')
  } finally {
    assignLoading.value = false
  }
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