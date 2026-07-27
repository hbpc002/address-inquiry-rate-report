<template>
  <div class="training-records">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>培训记录</span>
          <el-space>
            <el-button v-if="userStore.hasPermission('training_records.view')" @click="loadData">刷新</el-button>
            <el-button v-if="userStore.hasPermission('training_records.create')" type="primary" @click="openBatchDialog">批量录入</el-button>
          </el-space>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="日期范围">
          <el-date-picker v-model="searchForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" clearable style="width:140px" />
          <span style="margin: 0 8px">至</span>
          <el-date-picker v-model="searchForm.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" clearable style="width:140px" />
        </el-form-item>
        <el-form-item label="员工">
          <el-select v-model="searchForm.emp_no" filterable clearable placeholder="选择员工" style="width:160px">
            <el-option v-for="e in empOptions" :key="e.emp_no" :label="`${e.name} (${e.emp_no})`" :value="e.emp_no" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="searchForm.type" clearable placeholder="全部" style="width:100px">
            <el-option label="培训" value="培训" />
            <el-option label="请假" value="请假" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <div v-if="stats.total > 0" style="margin-bottom: 12px">
        <el-tag type="info">共 {{ stats.total }} 条记录</el-tag>
        <el-tag type="warning" style="margin-left: 8px">总时长: {{ stats.total_minutes }} 分钟 ({{ (stats.total_minutes / 60).toFixed(1) }}h)</el-tag>
      </div>

      <el-table :data="tableData" border stripe max-height="calc(100vh - 320px)">
        <el-table-column prop="emp_no" label="工号" width="90" />
        <el-table-column prop="record_date" label="日期" width="100" />
        <el-table-column label="起止时间" width="130">
          <template #default="{ row }">
            {{ row.start_time }} - {{ row.end_time }}
          </template>
        </el-table-column>
        <el-table-column prop="duration_minutes" label="时长(分钟)" width="90" sortable />
        <el-table-column prop="type" label="类型" width="70">
          <template #default="{ row }">
            <el-tag :type="row.type === '培训' ? 'primary' : 'warning'" size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_by" label="录入人" width="80" />
        <el-table-column prop="created_at" label="录入时间" width="160">
          <template #default="{ row }">
            {{ row.created_at?.slice(0, 19) }}
          </template>
        </el-table-column>
        <el-table-column v-if="userStore.hasPermission('training_records.delete')" label="操作" width="60" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="batchDialogVisible" title="批量录入培训/请假" width="650px">
      <el-form :model="batchForm" label-width="100px">
        <el-form-item label="选择员工" required>
          <el-select v-model="batchForm.selectedEmps" multiple filterable placeholder="请选择员工" style="width: 100%">
            <el-option v-for="e in empOptions" :key="e.emp_no" :label="`${e.name} (${e.emp_no} - ${e.team})`" :value="e.emp_no" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择日期" required>
          <el-date-picker v-model="batchForm.dates" type="dates" value-format="YYYY-MM-DD" multiple placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="开始时间" required>
          <el-time-picker v-model="batchForm.startTime" format="HH:mm" value-format="HH:mm" placeholder="选择开始时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" required>
          <el-time-picker v-model="batchForm.endTime" format="HH:mm" value-format="HH:mm" placeholder="选择结束时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="batchForm.type" style="width: 100%">
            <el-option label="培训" value="培训" />
            <el-option label="请假" value="请假" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="batchForm.reason" type="textarea" :rows="2" placeholder="请输入原因/备注" />
        </el-form-item>
      </el-form>
      <div style="font-size: 12px; color: #909399; margin-top: -8px; margin-bottom: 8px;">
        将创建 {{ batchForm.selectedEmps.length * batchForm.dates.length }} 条记录
      </div>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleBatchCreate" :disabled="!canSubmit">确认录入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api, useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'

const userStore = useUserStore()

const empOptions = ref([])
const tableData = ref([])
const stats = reactive({ total: 0, total_minutes: 0 })
const batchDialogVisible = ref(false)
const submitting = ref(false)

const searchForm = reactive({
  start_date: '',
  end_date: '',
  emp_no: '',
  type: ''
})

const batchForm = reactive({
  selectedEmps: [],
  dates: [],
  startTime: '',
  endTime: '',
  type: '培训',
  reason: ''
})

const canSubmit = computed(() => {
  return batchForm.selectedEmps.length > 0
    && batchForm.dates.length > 0
    && batchForm.startTime
    && batchForm.endTime
})

async function loadEmployees() {
  try {
    const res = await api.get('/employees', { params: { limit: 1000, status: '在职' } })
    empOptions.value = res.data.items || []
  } catch (e) {
    console.error(e)
  }
}

async function loadData() {
  try {
    const params = {}
    if (searchForm.start_date) params.start_date = searchForm.start_date
    if (searchForm.end_date) params.end_date = searchForm.end_date
    if (searchForm.emp_no) params.emp_no = searchForm.emp_no
    if (searchForm.type) params.type = searchForm.type
    const res = await api.get('/training-records', { params })
    tableData.value = res.data.items || []
    stats.total = res.data.total
    stats.total_minutes = res.data.total_minutes
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

function resetSearch() {
  searchForm.start_date = ''
  searchForm.end_date = ''
  searchForm.emp_no = ''
  searchForm.type = ''
  loadData()
}

function openBatchDialog() {
  batchForm.selectedEmps = []
  batchForm.dates = []
  batchForm.startTime = ''
  batchForm.endTime = ''
  batchForm.type = '培训'
  batchForm.reason = ''
  batchDialogVisible.value = true
}

async function handleBatchCreate() {
  if (!canSubmit.value) {
    ElMessage.warning('请填写完整信息')
    return
  }
  submitting.value = true
  try {
    const records = []
    for (const empNo of batchForm.selectedEmps) {
      for (const d of batchForm.dates) {
        records.push({
          emp_no: empNo,
          record_date: d,
          start_time: batchForm.startTime,
          end_time: batchForm.endTime,
          type: batchForm.type,
          reason: batchForm.reason || ''
        })
      }
    }
    await api.post('/training-records/batch', { records })
    ElMessage.success(`成功录入 ${records.length} 条记录`)
    batchDialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error('录入失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除 ${row.emp_no} ${row.record_date} 的记录？`, '确认删除')
    await api.delete(`/training-records/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

onMounted(() => {
  loadEmployees()
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
