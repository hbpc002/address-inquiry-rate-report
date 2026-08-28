<template>
  <div class="system">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="操作日志" name="logs">
        <el-card>
          <el-form inline>
            <el-form-item label="操作类型">
              <el-input v-model="searchLog.operation" placeholder="操作类型" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadLogs">查询</el-button>
            </el-form-item>
            <el-form-item>
              <el-button v-if="userStore.hasPermission('system.export_logs')" @click="exportLogs">导出日志</el-button>
            </el-form-item>
            <el-form-item>
              <el-select v-model="manualCleanupMonths" placeholder="清理月份" style="width:120px">
                <el-option v-for="n in [1,2,3,4,5,6]" :key="n" :label="n + ' 月'" :value="n"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button @click="manualCleanup" type="primary">执行清理</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="logs" border stripe>
            <el-table-column prop="created_at" label="操作时间" width="180">
              <template #default="{ row }">
                {{ row.created_at?.slice(0, 19) }}
              </template>
            </el-table-column>
            <el-table-column prop="user_id" label="操作人ID" width="100" />
            <el-table-column prop="user_name" label="操作人" width="100" />
            <el-table-column prop="operation_type" label="操作类型" width="100" />
            <el-table-column prop="target_table" label="目标表" width="120" />
            <el-table-column prop="target_id" label="目标ID" width="80" />
            <el-table-column prop="details" label="详情">
              <template #default="{ row }">
                {{ JSON.stringify(row.details) }}
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="logPagination.page"
            v-model:page-size="logPagination.limit"
            :total="logPagination.total"
            layout="total, prev, pager, next"
            @current-change="loadLogs"
          />
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="数据管理" name="data">
        <el-card>
          <template #header>
            <span>清空数据</span>
          </template>
          <el-alert type="warning" :closable="false" title="警告：此操作不可恢复，请谨慎操作！" />
          <el-form style="margin-top: 20px">
            <el-form-item label="选择表">
              <el-checkbox-group v-model="selectedTables">
                <el-checkbox label="employees">员工</el-checkbox>
                <el-checkbox label="schedules">排班</el-checkbox>
                <el-checkbox label="checkins">签到记录</el-checkbox>
                <el-checkbox label="daily_reports">考勤日报</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item>
              <el-button type="danger" @click="handleClearData" :disabled="selectedTables.length === 0">
                清空所选数据
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="更新日志" name="changelogs">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>更新日志管理</span>
              <el-button v-if="userStore.hasPermission('system.changelogs')" type="primary" @click="openChangelogCreate">新增日志</el-button>
            </div>
          </template>
          <el-table :data="changelogs" border stripe>
            <el-table-column prop="title" label="标题" width="160" />
            <el-table-column prop="content" label="内容" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ row.created_at?.slice(0, 16) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button v-if="userStore.hasPermission('system.changelogs')" type="primary" link @click="openChangelogEdit(row)">编辑</el-button>
                <el-button v-if="userStore.hasPermission('system.changelogs')" type="danger" link @click="handleDeleteChangelog(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="userStore.hasPermission('agent.config')" label="模型配置" name="llm">
        <LLMSettings />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="changelogDialogVisible" :title="changelogDialogTitle" width="600px">
      <el-form :model="changelogForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="changelogForm.title" placeholder="例如：v1.2.0" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="changelogForm.content" type="textarea" :rows="4" placeholder="例如：新增仪表盘数据更新日期显示 / 新增公告功能" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changelogDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingChangelog" @click="saveChangelog">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../stores/user'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import LLMSettings from './LLMSettings.vue'

const userStore = useUserStore()

const activeTab = ref('logs')
const logs = ref([])
const changelogs = ref([])
const manualCleanupMonths = ref(3)
const searchLog = reactive({ operation: '' })
const selectedTables = ref([])
const logPagination = reactive({ page: 1, limit: 20, total: 0 })
const changelogDialogVisible = ref(false)
const changelogDialogTitle = ref('')
const changelogForm = ref({ id: null, title: '', content: '' })
const savingChangelog = ref(false)

async function loadLogs() {
  try {
    const res = await api.get('/logs', { params: { ...searchLog, page: logPagination.page, limit: logPagination.limit } })
    logs.value = res.data.items
    logPagination.total = res.data.total
  } catch (e) {
    console.error(e)
  }
}

async function exportLogs() {
  try {
    const res = await api.get('/logs/export', { params: searchLog, responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `operation_logs_${new Date().toISOString().slice(0,10)}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
  }
}

async function manualCleanup() {
  try {
    const res = await api.post('/logs/cleanup', { months: manualCleanupMonths.value })
    ElMessage.success(`清理完成，删除 ${res.data.deleted} 条日志`)
  } catch (e) {
    ElMessage.error('清理失败')
  }
}

async function handleClearData() {
  if (selectedTables.value.length === 0) {
    ElMessage.warning('请选择要清空的表')
    return
  }
  try {
    await ElMessageBox.confirm(`确定要清空以下数据吗？\n${selectedTables.value.join(', ')}\n此操作不可恢复！`, '警告', { type: 'warning', confirmButtonText: '确定清空', cancelButtonText: '取消' })
    const res = await api.delete('/clear-data', { params: { tables: selectedTables.value.join(',') } })
    ElMessage.success('数据已清空')
    selectedTables.value = []
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('清空失败')
    }
  }
}

async function loadChangelogs() {
  try {
    const res = await api.get('/announcements', { params: { type: '更新日志', limit: 100 } })
    changelogs.value = res.data.items || []
  } catch (e) {
    console.error(e)
  }
}

function openChangelogCreate() {
  changelogForm.value = { id: null, title: '', content: '' }
  changelogDialogTitle.value = '新增更新日志'
  changelogDialogVisible.value = true
}

function openChangelogEdit(row) {
  changelogForm.value = { id: row.id, title: row.title, content: row.content }
  changelogDialogTitle.value = '编辑更新日志'
  changelogDialogVisible.value = true
}

async function saveChangelog() {
  if (!changelogForm.value.title || !changelogForm.value.content) {
    ElMessage.warning('请填写完整')
    return
  }
  savingChangelog.value = true
  try {
    if (changelogForm.value.id) {
      await api.put(`/announcements/${changelogForm.value.id}`, { title: changelogForm.value.title, content: changelogForm.value.content })
      ElMessage.success('更新日志已更新')
    } else {
      await api.post('/announcements', { title: changelogForm.value.title, content: changelogForm.value.content, type: '更新日志' })
      ElMessage.success('更新日志已创建')
    }
    changelogDialogVisible.value = false
    loadChangelogs()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingChangelog.value = false
  }
}

async function handleDeleteChangelog(row) {
  try {
    await ElMessageBox.confirm(`确定要删除更新日志"${row.title}"吗？`, '提示', { type: 'warning' })
    await api.delete(`/announcements/${row.id}`)
    ElMessage.success('已删除')
    loadChangelogs()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadChangelogs()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
