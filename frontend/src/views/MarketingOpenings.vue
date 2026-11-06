<template>
  <div class="marketing-openings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.marketing_opening }}</span>
          <div>
            <el-button v-if="userStore.hasPermission('marketing_opening.export')" type="success" @click="handleExport">导出开口率明细</el-button>
            <el-button v-if="userStore.hasPermission('marketing_opening.upload')" type="primary" @click="dialogVisible = true">导入开口数据</el-button>
          </div>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="录音日期">
          <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" style="width: 240px" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="searchForm.emp_no" placeholder="员工工号" clearable style="width: 130px" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="员工姓名" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="班组">
          <el-input v-model="searchForm.team" placeholder="源表/系统班组" clearable style="width: 150px" />
        </el-form-item>
        <el-form-item label="五大产品已开口">
          <el-select v-model="searchForm.opened" placeholder="全部" clearable style="width: 100px">
            <el-option label="是" value="是" />
            <el-option label="否" value="否" />
          </el-select>
        </el-form-item>
        <el-form-item label="批次">
          <el-input v-model="searchForm.batch" placeholder="批次号" clearable style="width: 110px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <el-space style="margin-bottom: 12px">
        <el-button v-if="userStore.hasPermission('marketing_opening.delete')" type="danger" @click="deleteByDateVisible = true">按录音日期删除</el-button>
        <el-button v-if="userStore.hasPermission('marketing_opening.delete')" type="danger" :disabled="!searchForm.batch" @click="handleDeleteBatch">按批次删除</el-button>
      </el-space>

      <el-table :data="tableData" border stripe max-height="calc(100vh - 360px)">
        <el-table-column prop="record_time" label="录音时间" width="165" />
        <el-table-column prop="contact_id" label="接触记录号" min-width="190" show-overflow-tooltip />
        <el-table-column prop="emp_no" label="员工工号" width="120" />
        <el-table-column prop="name" label="姓名" width="90" />
        <el-table-column prop="team" label="源表班组" min-width="140" show-overflow-tooltip />
        <el-table-column prop="system_team" label="系统班组" min-width="130" show-overflow-tooltip />
        <el-table-column v-for="column in openingColumns" :key="column.key" :prop="column.key" :label="column.label" width="120" />
        <el-table-column prop="five_products_opened" label="五大产品已开口" width="120" />
        <el-table-column prop="import_batch" label="批次" width="90" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('marketing_opening.delete')" type="danger" link @click="handleDelete(row)">删除</el-button>
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

    <el-dialog v-if="userStore.hasPermission('marketing_opening.upload')" v-model="dialogVisible" title="导入开口数据" width="560px" @closed="closeDialog">
      <el-upload
        drag
        :auto-upload="false"
        multiple
        accept=".xlsx,.xls,.csv,.CSV"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽“大模型质检台导出”文件到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 XLSX/CSV；按录音日期覆盖同日数据，按接触记录号去重</div>
        </template>
      </el-upload>
      <div v-if="uploadResults.length" style="margin-top: 12px">
        <el-tag v-for="r in uploadResults" :key="r.file" :type="r.success ? 'success' : 'danger'" style="margin: 2px; white-space: normal; height: auto; line-height: 1.4; padding: 4px 8px">
          {{ r.file }} → {{ r.success ? `批次 ${r.batch}，导入${r.count}条，跳过${r.skipped}条` : r.error }}
        </el-tag>
      </div>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteByDateVisible" title="按录音日期删除" width="360px">
      <el-date-picker v-model="deleteDate" type="date" value-format="YYYY-MM-DD" placeholder="选择录音日期" style="width: 100%" />
      <template #footer>
        <el-button @click="deleteByDateVisible = false">取消</el-button>
        <el-button type="danger" :loading="deletingByDate" @click="handleDeleteByDate">确认删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api, useUserStore } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { downloadBlob } from '../utils/download'

const userStore = useUserStore()
const ui = useUiConfigStore()
const tableData = ref([])
const dialogVisible = ref(false)
const uploading = ref(false)
const deleteByDateVisible = ref(false)
const deleteDate = ref('')
const deletingByDate = ref(false)
const searchForm = reactive({ batch: '', emp_no: '', name: '', team: '', opened: '' })
const range = ref('')
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const fileList = ref([])
const uploadResults = ref([])
const openingColumns = [
  { key: 'active_overlay', label: '叠加包主动' },
  { key: 'opened_overlay', label: '叠加包已开' },
  { key: 'active_broadband', label: '宽带主动' },
  { key: 'opened_broadband', label: '宽带已开' },
  { key: 'active_mobile_new', label: '移网新装主动' },
  { key: 'opened_mobile_new', label: '移网新装已开' },
  { key: 'active_terminal', label: '终端主动' },
  { key: 'opened_terminal', label: '终端已开' },
  { key: 'active_package', label: '套餐主动' },
  { key: 'opened_package', label: '套餐已开' }
]

function buildSearchParams() {
  const params = {
    import_batch: searchForm.batch || undefined,
    emp_no: searchForm.emp_no || undefined,
    name: searchForm.name || undefined,
    team: searchForm.team || undefined,
    five_products_opened: searchForm.opened || undefined
  }
  if (range.value && range.value.length === 2) {
    params.start_date = range.value[0]
    params.end_date = range.value[1]
  }
  return params
}

async function loadData() {
  try {
    const res = await api.get('/marketing-openings', {
      params: { ...buildSearchParams(), page: pagination.page, limit: pagination.limit }
    })
    tableData.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

function handleExport() {
  downloadBlob('/marketing-openings/export', buildSearchParams(), '开口率明细.csv')
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

function resetSearch() {
  searchForm.batch = ''
  searchForm.emp_no = ''
  searchForm.name = ''
  searchForm.team = ''
  searchForm.opened = ''
  range.value = ''
  pagination.page = 1
  loadData()
}

function handleFileChange(file, files) {
  fileList.value = files.map(f => ({ name: f.name, raw: f.raw }))
}

function handleFileRemove(file, files) {
  fileList.value = files.map(f => ({ name: f.name, raw: f.raw }))
}

async function handleUpload() {
  if (!fileList.value.length) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  uploadResults.value = []
  let successCount = 0
  let failCount = 0
  for (const f of fileList.value) {
    try {
      const formData = new FormData()
      formData.append('file', f.raw)
      const res = await api.post('/marketing-openings/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      uploadResults.value.push({
        file: f.name,
        success: true,
        batch: res.data.batch,
        count: res.data.count,
        skipped: res.data.skipped
      })
      successCount++
    } catch (e) {
      uploadResults.value.push({ file: f.name, success: false, error: e.response?.data?.detail || '导入失败' })
      failCount++
    }
  }
  uploading.value = false
  if (failCount === 0) {
    ElMessage.success(`全部导入成功，共${successCount}个文件`)
  } else {
    ElMessage.warning(`${successCount}个文件成功，${failCount}个文件失败`)
  }
  pagination.page = 1
  loadData()
}

function closeDialog() {
  dialogVisible.value = false
  fileList.value = []
  uploadResults.value = []
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该开口记录吗?', '提示', { type: 'warning' })
    await api.delete(`/marketing-openings/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function handleDeleteBatch() {
  if (!searchForm.batch) return
  try {
    await ElMessageBox.confirm(`确定要删除批次 "${searchForm.batch}" 的开口记录吗？`, '提示', { type: 'warning' })
    const res = await api.delete(`/marketing-openings/import/${searchForm.batch}`)
    ElMessage.success(`已删除${res.data.count}条记录`)
    loadData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function handleDeleteByDate() {
  if (!deleteDate.value) {
    ElMessage.warning('请选择日期')
    return
  }
  try {
    await ElMessageBox.confirm(`确定要删除 ${deleteDate.value} 的所有开口记录吗？`, '提示', { type: 'warning' })
    deletingByDate.value = true
    const res = await api.delete('/marketing-openings/by-date', { params: { date: deleteDate.value } })
    ElMessage.success(`已删除${res.data.count}条记录`)
    deleteByDateVisible.value = false
    deleteDate.value = ''
    loadData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    deletingByDate.value = false
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
