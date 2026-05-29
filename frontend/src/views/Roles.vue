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
                v-for="(val, key) in parsePermissions(row.permissions)"
                :key="key"
                size="small"
                style="margin: 2px"
                :type="val ? 'success' : 'info'"
              >
                {{ permissionLabel(key) }}
              </el-tag>
              <span v-if="!row.permissions || Object.keys(parsePermissions(row.permissions)).length === 0">无</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('roles.manage') && !row.is_system" type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="userStore.hasPermission('roles.manage') && !row.is_system" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑角色' : '新增角色'" width="700px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="角色名称">
          <el-input v-model="form.name" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="权限">
          <el-checkbox :indeterminate="isIndeterminate" :model-value="checkAll" @change="handleCheckAll">全选</el-checkbox>
          <el-divider />
          <div v-for="(pageInfo, pageKey) in PERMISSION_REGISTRY" :key="pageKey" style="margin-bottom: 12px">
            <div style="font-weight: bold; margin-bottom: 6px; color: #606266">{{ pageInfo.label }}</div>
            <el-checkbox-group v-model="form.permissions">
              <el-checkbox v-for="(label, action) in pageInfo.permissions" :key="`${pageKey}.${action}`" :label="`${pageKey}.${action}`">
                {{ label }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../stores/user'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PERMISSION_REGISTRY, getAllPermissionKeys, permissionLabel } from '../permissions'

const userStore = useUserStore()

const tableData = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive({ id: null, name: '', description: '', permissions: [] })

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