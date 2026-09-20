<template>
  <div class="broadband-orders">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>无缝订单</span>
          <div>
            <el-button v-if="userStore.hasPermission('broadband.upload')" type="primary" @click="dialogVisible = true">导入无缝订单</el-button>
          </div>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="下单日期范围">
          <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" style="width: 240px" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="searchForm.emp_no" placeholder="请输入工号" clearable style="width: 130px" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="请输入姓名" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="导入批次">
          <el-input v-model="searchForm.batch" placeholder="批次号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <el-space style="margin-bottom: 12px">
        <el-button v-if="userStore.hasPermission('broadband.delete')" type="danger" @click="deleteByDateVisible = true">按日期删除</el-button>
        <el-button v-if="userStore.hasPermission('broadband.delete')" type="danger" :disabled="!searchForm.batch" @click="handleDeleteBatch">按批次删除</el-button>
      </el-space>

      <el-table :data="tableData" border stripe max-height="calc(100vh - 320px)">
        <el-table-column prop="order_date" label="下单日期" width="100" />
        <el-table-column prop="order_no" label="无缝订单号" min-width="150" />
        <el-table-column prop="emp_no" label="下单工号" width="120" />
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column prop="team" label="班组" min-width="130" />
        <el-table-column prop="is_completed" label="是否竣工" width="80" />
        <el-table-column prop="is_excluded" label="是否剔除" width="80" />
        <el-table-column prop="is_duplicate" label="是否重复单" width="85" />
        <el-table-column prop="is_hour_short" label="1小时短单" width="85" />
        <el-table-column prop="city" label="地市" width="70" />
        <el-table-column prop="order_status" label="订单状态" width="90" />
        <el-table-column prop="cb_order_status" label="CB订单状态" width="90" />
        <el-table-column prop="product_name" label="产品名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="bandwidth_speed" label="宽带速率" width="70" />
        <el-table-column prop="intention_emp_no" label="意向单受理人" width="120" />
        <el-table-column prop="import_batch" label="批次号" width="100" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('broadband.delete')" type="danger" link @click="handleDelete(row)">删除</el-button>
            <el-button v-if="userStore.hasPermission('broadband.delete')" type="danger" link @click="handleDeleteBatchByValue(row.import_batch)">删除本批次</el-button>
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

    <el-dialog v-if="userStore.hasPermission('broadband.upload')" v-model="dialogVisible" title="导入无缝订单数据" width="520px" @closed="closeDialog">
      <el-upload
        ref="upload"
        drag
        :auto-upload="false"
        multiple
        accept=".xlsx,.XLSX"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽XLSX文件到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">格式：新客服无缝订单-原始表.XLSX（第3行为表头）</div>
        </template>
      </el-upload>
      <div v-if="uploadResults.length" style="margin-top: 12px">
        <el-tag v-for="r in uploadResults" :key="r.file" :type="r.success ? 'success' : 'danger'" style="margin: 2px; white-space: normal; height: auto; line-height: 1.4; padding: 4px 8px">
          {{ r.file }} → {{ r.success ? `批次 ${r.batch}，导入${r.count}条` : r.error }}
        </el-tag>
      </div>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteByDateVisible" title="按日期删除" width="360px">
      <el-date-picker v-model="deleteDate" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width: 100%" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

const userStore = useUserStore()
const tableData = ref([])
const dialogVisible = ref(false)
const uploading = ref(false)
const deleteByDateVisible = ref(false)
const deleteDate = ref('')
const deletingByDate = ref(false)
const searchForm = reactive({ batch: '', emp_no: '', name: '' })
const range = ref('')
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const fileList = ref([])
const uploadResults = ref([])

async function loadData() {
  try {
    const params = {
      page: pagination.page,
      limit: pagination.limit,
      import_batch: searchForm.batch || undefined,
      name: searchForm.name || undefined,
      emp_no: searchForm.emp_no || undefined
    }
    if (range.value && range.value.length === 2) {
      params.start_date = range.value[0]
      params.end_date = range.value[1]
    }
    const res = await api.get('/broadband/orders', { params })
    tableData.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

function resetSearch() {
  searchForm.batch = ''
  searchForm.emp_no = ''
  searchForm.name = ''
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
      const res = await api.post('/broadband/orders/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      uploadResults.value.push({ file: f.name, success: true, batch: res.data.batch, count: res.data.count })
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
  loadData()
}

function closeDialog() {
  dialogVisible.value = false
  fileList.value = []
  uploadResults.value = []
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该记录吗?', '提示', { type: 'warning' })
    await api.delete(`/broadband/orders/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleDeleteBatchByValue(batch) {
  if (!batch) return
  try {
    await ElMessageBox.confirm(`确定要删除批次 "${batch}" 的所有记录吗？`, '提示', { type: 'warning' })
    const res = await api.delete(`/broadband/orders/import/${batch}`)
    ElMessage.success(`已删除${res.data.count}条记录`)
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleDeleteBatch() {
  if (!searchForm.batch) return
  await handleDeleteBatchByValue(searchForm.batch)
}

async function handleDeleteByDate() {
  if (!deleteDate.value) {
    ElMessage.warning('请选择日期')
    return
  }
  try {
    await ElMessageBox.confirm(`确定要删除 ${deleteDate.value} 的所有无缝订单记录吗？`, '提示', { type: 'warning' })
    deletingByDate.value = true
    const res = await api.delete('/broadband/orders/by-date', { params: { date: deleteDate.value } })
    ElMessage.success(`已删除${res.data.count}条记录`)
    deleteByDateVisible.value = false
    deleteDate.value = ''
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  } finally {
    deletingByDate.value = false
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