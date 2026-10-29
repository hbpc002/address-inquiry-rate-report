<template>
  <div class="roles">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.roles }}</span>
          <el-button v-if="userStore.hasPermission('roles.manage')" type="primary" @click="handleAdd">新增角色</el-button>
        </div>
      </template>

      <el-table :data="tableData" border stripe>
        <el-table-column prop="name" label="角色名称" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_system ? 'danger' : 'warning'">{{ row.name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" width="180" />
        <el-table-column label="数据范围" width="130">
          <template #default="{ row }">
            <el-tag :type="row.data_scope === 'dept' ? 'warning' : 'success'">
              {{ row.data_scope === 'dept' ? '本部门数据' : '全部数据' }}
            </el-tag>
          </template>
        </el-table-column>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑角色' : '新增角色'" width="860px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="角色名称">
          <el-input v-model="form.name" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="数据范围">
          <el-radio-group v-model="form.data_scope">
            <el-radio value="all">全部数据</el-radio>
            <el-radio value="dept">仅本部门数据</el-radio>
          </el-radio-group>
          <div class="form-tip">
            “仅本部门数据”需要同时在用户管理中给用户填写所属部门，按部门路径前缀匹配。
          </div>
        </el-form-item>
        <el-form-item label="权限">
          <div style="margin-bottom: 12px">
            <el-checkbox :indeterminate="isIndeterminate" :model-value="checkAll" @change="handleCheckAll">全选所有权限</el-checkbox>
          </div>
          <div v-for="group in permissionGroups" :key="group.group" class="permission-group">
            <div class="permission-group-header">
              <span class="permission-group-title">{{ group.group }}</span>
              <el-checkbox
                :indeterminate="isPermissionGroupIndeterminate(group)"
                :model-value="isPermissionGroupAllChecked(group)"
                @change="val => handlePermissionGroupCheckAll(group, val)"
                size="small"
              >全选本组</el-checkbox>
            </div>
            <el-card
              v-for="page in group.pages"
              :key="page.pageKey"
              shadow="hover"
              body-style="padding: 12px"
              class="permission-page-card"
            >
              <template #header>
                <div class="permission-page-header">
                  <span class="permission-page-title">{{ page.label }}</span>
                  <el-checkbox
                    :indeterminate="isGroupIndeterminate(page.pageKey)"
                    :model-value="isGroupAllChecked(page.pageKey)"
                    @change="val => handleGroupCheckAll(page.pageKey, val)"
                    size="small"
                  >全选</el-checkbox>
                </div>
              </template>
              <el-checkbox-group v-model="form.permissions">
                <el-checkbox
                  v-for="(label, action) in page.permissions"
                  :key="`${page.pageKey}.${action}`"
                  :label="`${page.pageKey}.${action}`"
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
              :label="formatUserLabel(u)"
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
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PERMISSION_REGISTRY, getAllPermissionKeys } from '../permissions'

const userStore = useUserStore()
const ui = useUiConfigStore()

const registry = ref(PERMISSION_REGISTRY)
const tableData = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive({ id: null, name: '', description: '', data_scope: 'all', permissions: [] })

const assignDialogVisible = ref(false)
const assignRole = ref(null)
const assignUserIds = ref([])
const allUsers = ref([])
const assignLoading = ref(false)

const allKeys = computed(() => {
  const keys = []
  for (const [page, info] of Object.entries(registry.value)) {
    for (const action of Object.keys(info.permissions)) {
      keys.push(`${page}.${action}`)
    }
  }
  return keys.length ? keys : getAllPermissionKeys()
})

const permissionGroups = computed(() => {
  const groups = new Map()
  const pages = Object.entries(registry.value).sort((a, b) => (a[1].order || 0) - (b[1].order || 0))
  for (const [pageKey, pageInfo] of pages) {
    const groupName = pageInfo.group || '其他'
    if (!groups.has(groupName)) groups.set(groupName, [])
    groups.get(groupName).push({ pageKey, ...pageInfo })
  }
  return Array.from(groups.entries()).map(([group, pages]) => ({ group, pages }))
})

const checkAll = computed(() => allKeys.value.length > 0 && form.permissions.length === allKeys.value.length)
const isIndeterminate = computed(() => form.permissions.length > 0 && form.permissions.length < allKeys.value.length)

function handleCheckAll(val) {
  form.permissions = val ? [...allKeys.value] : []
}

function parsePermissions(permissions) {
  try {
    const obj = JSON.parse(permissions || '{}')
    const sorted = {}
    for (const key of allKeys.value) {
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
    return Object.entries(registry.value).map(([pageKey, pageInfo]) => {
      const actions = Object.keys(pageInfo.permissions)
      const enabledCount = actions.filter(a => obj[`${pageKey}.${a}`] === true).length
      return { pageKey, label: pageInfo.label, enabled: enabledCount, total: actions.length }
    })
  } catch {
    return []
  }
}

function getGroupKeys(pageKey) {
  const pageInfo = registry.value[pageKey]
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

function getPermissionGroupKeys(group) {
  return group.pages.flatMap(page => getGroupKeys(page.pageKey))
}

function isPermissionGroupAllChecked(group) {
  const keys = getPermissionGroupKeys(group)
  return keys.length > 0 && keys.every(k => form.permissions.includes(k))
}

function isPermissionGroupIndeterminate(group) {
  const keys = getPermissionGroupKeys(group)
  const checkedCount = keys.filter(k => form.permissions.includes(k)).length
  return checkedCount > 0 && checkedCount < keys.length
}

function handlePermissionGroupCheckAll(group, checked) {
  const keys = getPermissionGroupKeys(group)
  if (checked) {
    const toAdd = keys.filter(k => !form.permissions.includes(k))
    form.permissions.push(...toAdd)
  } else {
    form.permissions = form.permissions.filter(k => !keys.includes(k))
  }
}

function formatUserLabel(user) {
  const base = user.display_name ? `${user.username} (${user.display_name})` : user.username
  return user.dept ? `${base} - ${user.dept}` : base
}

async function loadRegistry() {
  try {
    const res = await api.get('/roles/permissions')
    if (res.data && Object.keys(res.data).length) {
      registry.value = res.data
    }
  } catch (e) {
    registry.value = PERMISSION_REGISTRY
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
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    data_scope: 'all',
    permissions: [...allKeys.value],
  })
  isEdit.value = false
  dialogVisible.value = true
}

function handleEdit(row) {
  const perms = parsePermissions(row.permissions)
  Object.assign(form, {
    id: row.id,
    name: row.name,
    description: row.description,
    data_scope: row.data_scope || 'all',
    permissions: Object.keys(perms),
  })
  isEdit.value = true
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    const permObj = {}
    form.permissions.forEach(p => { permObj[p] = true })
    for (const key of allKeys.value) {
      if (!permObj[key]) permObj[key] = false
    }
    if (isEdit.value) {
      await api.put(`/roles/${form.id}`, {
        permissions: permObj,
        description: form.description,
        data_scope: form.data_scope,
      })
      ElMessage.success('更新成功')
    } else {
      await api.post('/roles', {
        name: form.name,
        description: form.description,
        data_scope: form.data_scope,
        permissions: permObj,
      })
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
    await api.put(`/roles/${assignRole.value.id}/users`, { user_ids: assignUserIds.value })
    ElMessage.success('分配成功')
    assignDialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '分配失败')
  } finally {
    assignLoading.value = false
  }
}

onMounted(async () => {
  await loadRegistry()
  loadData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  width: 100%;
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}

.permission-group {
  width: 100%;
  margin-bottom: 16px;
}

.permission-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.permission-group-title {
  font-weight: bold;
  color: #303133;
}

.permission-page-card {
  margin-bottom: 8px;
}

.permission-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.permission-page-title {
  font-weight: bold;
}
</style>
