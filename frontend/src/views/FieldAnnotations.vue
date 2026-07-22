<template>
  <div class="field-annotations">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>字段批注管理</span>
          <el-button v-if="userStore.hasPermission('field_annotations.edit')" type="primary" @click="openCreate">新增批注</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="报表类型">
          <el-select v-model="filterReportType" placeholder="全部" clearable @change="loadData">
            <el-option label="日报表" value="daily" />
            <el-option label="月度汇总" value="monthly" />
            <el-option label="工作量报表" value="workload" />
            <el-option label="签入签出报表" value="checkin" />
            <el-option label="效能报表" value="efficiency" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-table :data="annotations" border stripe v-loading="loading" max-height="600">
        <el-table-column prop="report_type" label="报表" width="100">
          <template #default="{ row }">
            {{ reportTypeLabel(row.report_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="field_label" label="字段名" width="150" />
        <el-table-column prop="field_path" label="字段标识" width="180" />
        <el-table-column prop="source" label="数据来源" min-width="200" show-overflow-tooltip />
        <el-table-column prop="formula" label="计算公式" min-width="220" show-overflow-tooltip />
        <el-table-column prop="description" label="口径说明" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('field_annotations.edit')" type="primary" link @click="openEdit(row)">编辑</el-button>
            <el-button v-if="userStore.hasPermission('field_annotations.edit')" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑批注' : '新增批注'" width="650px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="报表类型">
          <el-select v-model="form.report_type">
            <el-option label="日报表" value="daily" />
            <el-option label="月度汇总" value="monthly" />
            <el-option label="工作量报表" value="workload" />
            <el-option label="签入签出报表" value="checkin" />
            <el-option label="效能报表" value="efficiency" />
          </el-select>
        </el-form-item>
        <el-form-item label="字段标识">
          <el-input v-model="form.field_path" placeholder="如 actual_hours" />
        </el-form-item>
        <el-form-item label="字段显示名">
          <el-input v-model="form.field_label" placeholder="如 实际工时" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="数据来源">
          <el-input v-model="form.source" type="textarea" :rows="2" placeholder="描述字段数据的来源" />
        </el-form-item>
        <el-form-item label="计算公式">
          <el-input v-model="form.formula" type="textarea" :rows="3" placeholder="描述字段的计算逻辑" />
        </el-form-item>
        <el-form-item label="口径说明">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="补充说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
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
const loading = ref(false)
const saving = ref(false)
const annotations = ref([])
const filterReportType = ref('')
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)

const defaultForm = () => ({
  report_type: 'daily',
  field_path: '',
  field_label: '',
  source: '',
  formula: '',
  description: '',
  sort_order: 0,
})

const form = reactive(defaultForm())

function reportTypeLabel(type) {
  const map = { daily: '日报表', monthly: '月度汇总', workload: '工作量报表', checkin: '签入签出报表', efficiency: '效能报表' }
  return map[type] || type
}

async function loadData() {
  loading.value = true
  try {
    const params = { limit: 500 }
    if (filterReportType.value) params.report_type = filterReportType.value
    const res = await api.get('/field-annotations', { params })
    annotations.value = res.data.items || []
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEditing.value = false
  editingId.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function openEdit(row) {
  isEditing.value = true
  editingId.value = row.id
  Object.assign(form, {
    report_type: row.report_type,
    field_path: row.field_path,
    field_label: row.field_label,
    source: row.source || '',
    formula: row.formula || '',
    description: row.description || '',
    sort_order: row.sort_order ?? 0,
  })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) {
      await api.put(`/field-annotations/${editingId.value}`, form)
      ElMessage.success('已更新')
    } else {
      await api.post('/field-annotations', form)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除"${row.field_label}"的批注吗？`, '提示', { type: 'warning' })
    await api.delete(`/field-annotations/${row.id}`)
    ElMessage.success('已删除')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
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
</style>
