<template>
  <div class="department-groups">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>部门设置</span>
          <el-button v-if="userStore.hasPermission('department_groups.manage')" type="primary" @click="handleAdd">新增部门组</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="搜索">
          <el-input v-model="keyword" placeholder="部门组名称" clearable @keyup.enter="loadData" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" border stripe>
        <el-table-column prop="name" label="部门组名称" width="180" />
        <el-table-column prop="description" label="描述" width="200" show-overflow-tooltip />
        <el-table-column label="组织路径" min-width="360">
          <template #default="{ row }">
            <el-tag v-for="path in row.paths" :key="path" size="small" style="margin: 2px">
              {{ path }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="user_count" label="用户数" width="90" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('department_groups.manage')" type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="userStore.hasPermission('department_groups.manage')" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑部门组' : '新增部门组'" width="680px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="部门组名称">
          <el-input v-model="form.name" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="组织路径">
          <div class="path-list">
            <div v-for="(path, index) in form.paths" :key="index" class="path-row">
              <el-input v-model="form.paths[index]" placeholder="例如：广西分公司>>省中心>>客户服务营销中心>>热线运营组" />
              <el-button type="danger" link :disabled="form.paths.length <= 1" @click="removePath(index)">删除</el-button>
            </div>
            <el-button type="primary" link @click="addPath">+ 添加组织路径</el-button>
            <div class="form-tip">路径按前缀匹配，配置上级路径会包含其下所有下级部门。</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, useUserStore } from '../stores/user'

const userStore = useUserStore()
const tableData = ref([])
const keyword = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const form = reactive({ id: null, name: '', description: '', is_active: true, paths: [''] })

function addPath() {
  form.paths.push('')
}

function removePath(index) {
  form.paths.splice(index, 1)
}

async function loadData() {
  try {
    const res = await api.get('/department-groups', { params: { keyword: keyword.value } })
    tableData.value = res.data.items || []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

function handleAdd() {
  Object.assign(form, { id: null, name: '', description: '', is_active: true, paths: [''] })
  isEdit.value = false
  dialogVisible.value = true
}

function handleEdit(row) {
  Object.assign(form, {
    id: row.id,
    name: row.name,
    description: row.description || '',
    is_active: row.is_active,
    paths: row.paths?.length ? [...row.paths] : [''],
  })
  isEdit.value = true
  dialogVisible.value = true
}

async function handleSubmit() {
  const paths = form.paths.map(item => item.trim()).filter(Boolean)
  if (!form.name.trim()) {
    ElMessage.warning('请填写部门组名称')
    return
  }
  if (!paths.length) {
    ElMessage.warning('请至少配置一个组织路径')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description,
      is_active: form.is_active,
      paths,
    }
    if (isEdit.value) {
      await api.put(`/department-groups/${form.id}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/department-groups', payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除部门组"${row.name}"吗？`, '提示', { type: 'warning' })
    await api.delete(`/department-groups/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(loadData)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.path-list {
  width: 100%;
}

.path-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.form-tip {
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}
</style>
