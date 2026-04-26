<template>
  <div class="system">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="班次类型" name="shifts">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>班次类型管理</span>
              <el-button type="primary" @click="handleAddShift">新增班次</el-button>
            </div>
          </template>

          <el-table :data="shiftTypes" border stripe>
            <el-table-column prop="shift_name" label="班次名称" width="120" />
            <el-table-column prop="start_time" label="开始时间" width="100" />
            <el-table-column prop="end_time" label="结束时间" width="100" />
            <el-table-column prop="work_hours" label="工作时长" width="100" />
            <el-table-column prop="color" label="颜色" width="100">
              <template #default="{ row }">
                <div :style="{ backgroundColor: row.color, width: '20px', height: '20px' }"></div>
              </template>
            </el-table-column>
            <el-table-column prop="is_night" label="夜班" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_night ? 'danger' : 'info'">{{ row.is_night ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button type="primary" link @click="handleEditShift(row)">编辑</el-button>
                <el-button type="danger" link @click="handleDeleteShift(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

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
              <el-button @click="exportLogs">导出日志</el-button>
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
            <el-table-column prop="operation_type" label="操作类型" width="100" />
            <el-table-column prop="target_table" label="目标表" width="120" />
            <el-table-column prop="target_id" label="目标ID" width="80" />
            <el-table-column prop="details" label="详情">
              <template #default="{ row }">
                {{ JSON.stringify(row.details) }}
              </template>
            </el-table-column>
          </el-table>
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
    </el-tabs>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑班次' : '新增班次'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="班次名称">
          <el-input v-model="form.shift_name" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-picker v-model="form.start_time" value-format="HH:mm" placeholder="选择时间" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker v-model="form.end_time" value-format="HH:mm" placeholder="选择时间" />
        </el-form-item>
        <el-form-item label="工作时长">
          <el-input-number v-model="form.work_hours" :min="0" :max="24" :step="0.5" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="form.color" />
        </el-form-item>
        <el-form-item label="夜班">
          <el-switch v-model="form.is_night" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitShift">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('shifts')
const shiftTypes = ref([])
const logs = ref([])
const manualCleanupMonths = ref(3)
const dialogVisible = ref(false)
const isEdit = ref(false)
const searchLog = reactive({ operation: '' })
const selectedTables = ref([])
const form = reactive({
  id: null,
  shift_name: '',
  start_time: '',
  end_time: '',
  work_hours: 8,
  color: '#409EFF',
  is_night: false
})

async function loadShiftTypes() {
  try {
    const res = await api.get('/shift-types')
    shiftTypes.value = res.data
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

async function loadLogs() {
  try {
    const res = await api.get('/logs', { params: searchLog })
    logs.value = res.data.items
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

function handleAddShift() {
  Object.assign(form, { id: null, shift_name: '', start_time: '', end_time: '', work_hours: 8, color: '#409EFF', is_night: false })
  isEdit.value = false
  dialogVisible.value = true
}

function handleEditShift(row) {
  Object.assign(form, { ...row })
  isEdit.value = true
  dialogVisible.value = true
}

async function handleSubmitShift() {
  try {
    if (isEdit.value) {
      await api.put(`/shift-types/${form.id}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/shift-types', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadShiftTypes()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDeleteShift(row) {
  try {
    await ElMessageBox.confirm('确定要删除该班次吗?', '提示', { type: 'warning' })
    await api.delete(`/shift-types/${row.id}`)
    ElMessage.success('删除成功')
    loadShiftTypes()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
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

onMounted(() => {
  loadShiftTypes()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
