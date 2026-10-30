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
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('department_groups.manage')" type="success" link @click="handleAssign(row)">分配人员</el-button>
            <el-button v-if="userStore.hasPermission('department_groups.manage')" type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="userStore.hasPermission('department_groups.manage')" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="assignVisible" :title="assignGroup ? `分配人员 - ${assignGroup.name}` : '分配人员'" width="780px">
      <div class="assign-group-info">
        <span>组织路径：</span>
        <el-tag v-for="path in (assignGroup?.paths || [])" :key="path" size="small" style="margin: 2px">
          {{ path }}
        </el-tag>
      </div>
      <el-alert
        title="用户只能属于一个部门组。选择其他部门的人员加入后，会自动从原部门组转入当前部门组。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />
      <el-tabs v-model="assignTab">
        <el-tab-pane label="添加人员" name="add">
          <el-select
            v-model="assignSelectedUserIds"
            multiple
            filterable
            remote
            reserve-keyword
            clearable
            placeholder="搜索用户名或显示名"
            :remote-method="loadAvailableUsers"
            :loading="availableLoading"
            style="width: 100%"
          >
            <el-option
              v-for="user in availableUsers"
              :key="user.id"
              :label="userOptionLabel(user)"
              :value="user.id"
            >
              <span>{{ user.display_name || user.username }}（{{ user.username }}）</span>
              <span class="option-group">
                {{ user.department_group_name ? `当前：${user.department_group_name}` : '未分配部门' }}
              </span>
            </el-option>
          </el-select>
          <div class="form-tip">可添加启用状态的用户；已在当前部门组的人员不会出现在列表中。</div>
          <div class="assign-actions">
            <el-button
              type="primary"
              :loading="assigningAdd"
              :disabled="!assignSelectedUserIds.length"
              @click="handleAssignAdd"
            >
              加入部门
            </el-button>
          </div>
        </el-tab-pane>
        <el-tab-pane :label="`当前人员 (${memberTotal})`" name="members">
          <el-form inline>
            <el-form-item label="搜索">
              <el-input v-model="memberKeyword" placeholder="用户名/显示名" clearable @keyup.enter="handleMemberSearch" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleMemberSearch">查询</el-button>
              <el-button @click="resetMemberSearch">重置</el-button>
            </el-form-item>
          </el-form>
          <el-table :data="members" border stripe @selection-change="handleMemberSelectionChange">
            <el-table-column type="selection" width="50" />
            <el-table-column prop="username" label="用户名" width="140" />
            <el-table-column prop="display_name" label="显示名" min-width="140" />
            <el-table-column prop="role" label="角色" width="120" show-overflow-tooltip />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div class="member-footer">
            <el-button
              type="danger"
              :loading="assigningRemove"
              :disabled="!memberSelection.length"
              @click="handleAssignRemove"
            >
              移出选中
            </el-button>
            <el-pagination
              v-model:current-page="memberPage"
              v-model:page-size="memberLimit"
              :total="memberTotal"
              layout="total, prev, pager, next"
              @current-change="loadMembers"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="assignVisible = false">关闭</el-button>
      </template>
    </el-dialog>

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

const assignVisible = ref(false)
const assignGroup = ref(null)
const assignTab = ref('add')
const availableUsers = ref([])
const availableLoading = ref(false)
const assignSelectedUserIds = ref([])
const members = ref([])
const memberKeyword = ref('')
const memberTotal = ref(0)
const memberPage = ref(1)
const memberLimit = ref(10)
const memberSelection = ref([])
const assigningAdd = ref(false)
const assigningRemove = ref(false)

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

function userOptionLabel(user) {
  return `${user.display_name || user.username}（${user.username}）`
}

async function loadAvailableUsers(keyword = '') {
  if (!assignGroup.value) return
  availableLoading.value = true
  try {
    const res = await api.get(`/department-groups/${assignGroup.value.id}/available-users`, {
      params: { keyword: keyword || '' },
    })
    availableUsers.value = res.data || []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载可分配用户失败')
  } finally {
    availableLoading.value = false
  }
}

async function loadMembers() {
  if (!assignGroup.value) return
  try {
    const res = await api.get(`/department-groups/${assignGroup.value.id}/members`, {
      params: {
        keyword: memberKeyword.value,
        page: memberPage.value,
        limit: memberLimit.value,
      },
    })
    members.value = res.data.items || []
    memberTotal.value = res.data.total || 0
    if (!members.value.length && memberPage.value > 1) {
      memberPage.value -= 1
      await loadMembers()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载当前人员失败')
  }
}

async function handleAssign(row) {
  assignGroup.value = row
  assignTab.value = 'add'
  assignSelectedUserIds.value = []
  availableUsers.value = []
  members.value = []
  memberKeyword.value = ''
  memberPage.value = 1
  memberTotal.value = 0
  memberSelection.value = []
  assignVisible.value = true
  await Promise.all([loadAvailableUsers(''), loadMembers()])
}

function handleMemberSearch() {
  memberPage.value = 1
  loadMembers()
}

function resetMemberSearch() {
  memberKeyword.value = ''
  memberPage.value = 1
  loadMembers()
}

function handleMemberSelectionChange(rows) {
  memberSelection.value = rows
}

async function refreshAssignData() {
  assignSelectedUserIds.value = []
  memberSelection.value = []
  await Promise.all([loadAvailableUsers(''), loadMembers(), loadData()])
}

async function handleAssignAdd() {
  if (!assignGroup.value || !assignSelectedUserIds.value.length) return
  assigningAdd.value = true
  try {
    const res = await api.post(`/department-groups/${assignGroup.value.id}/members`, {
      user_ids: assignSelectedUserIds.value,
    })
    let message = `已加入 ${res.data.assigned} 人`
    if (res.data.skipped) message += `，跳过 ${res.data.skipped} 人`
    ElMessage.success(message)
    await refreshAssignData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加入部门失败')
  } finally {
    assigningAdd.value = false
  }
}

async function handleAssignRemove() {
  if (!assignGroup.value || !memberSelection.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定要将选中的 ${memberSelection.value.length} 名人员移出部门组"${assignGroup.value.name}"吗？`,
      '提示',
      { type: 'warning' },
    )
  } catch (e) {
    return
  }
  assigningRemove.value = true
  try {
    const res = await api.post(`/department-groups/${assignGroup.value.id}/members/remove`, {
      user_ids: memberSelection.value.map(item => item.id),
    })
    let message = `已移出 ${res.data.removed} 人`
    if (res.data.skipped) message += `，跳过 ${res.data.skipped} 人`
    ElMessage.success(message)
    await refreshAssignData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '移出人员失败')
  } finally {
    assigningRemove.value = false
  }
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

.assign-group-info {
  margin-bottom: 12px;
  color: #606266;
  font-size: 14px;
}

.option-group {
  float: right;
  margin-left: 16px;
  color: #909399;
  font-size: 12px;
}

.assign-actions {
  margin-top: 16px;
}

.member-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}
</style>
