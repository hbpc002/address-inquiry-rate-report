<template>
  <div class="workloads">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>工作量详单</span>
          <el-button v-if="userStore.hasPermission('workload.upload')" type="primary" @click="dialogVisible = true">导入工作量</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="日期">
          <el-date-picker v-model="searchForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" clearable />
        </el-form-item>
        <el-form-item label="账号">
          <el-input v-model="searchForm.account" placeholder="请输入账号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="请输入姓名" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="导入批次">
          <el-input v-model="searchForm.batch" placeholder="批次号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <el-space style="margin-bottom: 12px">
        <el-button v-if="userStore.hasPermission('workload.delete')" type="danger" @click="deleteByDateVisible = true">按日期删除</el-button>
        <el-button v-if="userStore.hasPermission('workload.delete')" type="danger" :disabled="!searchForm.batch" @click="handleDeleteBatch">按批次删除</el-button>
      </el-space>

      <el-table :data="tableData" border stripe>
        <el-table-column prop="date" label="日期" width="100">
          <template #default="{ row }">
            {{ row.date?.slice(0, 10) }}
          </template>
        </el-table-column>
        <el-table-column prop="province" label="省份" width="80" />
        <el-table-column prop="account" label="账号" width="110" />
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column prop="emp_no" label="工号" width="80" />
        <el-table-column prop="team_desc" label="班组" min-width="160" />
        <el-table-column prop="import_batch" label="批次号" width="100" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('workload.delete')" type="danger" link @click="handleDelete(row)">删除</el-button>
            <el-button v-if="userStore.hasPermission('workload.delete')" type="danger" link @click="handleDeleteBatchByValue(row.import_batch)">删除本批次</el-button>
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

    <el-dialog v-if="userStore.hasPermission('workload.upload')" v-model="dialogVisible" title="导入工作量数据" width="500px" @closed="closeDialog">
      <el-upload
        ref="upload"
        drag
        :auto-upload="false"
        multiple
        accept=".xlsx"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽XLSX文件到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">支持多文件同时拖入，格式：03客服代表工作量和操作情况统计表</div>
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
const searchForm = reactive({ batch: '', date: '', name: '', account: '' })
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const fileList = ref([])
const uploadResults = ref([])

async function loadData() {
  try {
    const params = {
      page: pagination.page,
      limit: pagination.limit,
      import_batch: searchForm.batch || undefined,
      workload_date: searchForm.date || undefined,
      name: searchForm.name || undefined,
      account: searchForm.account || undefined
    }
    const res = await api.get('/workloads', { params })
    tableData.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

function resetSearch() {
  searchForm.batch = ''
  searchForm.date = ''
  searchForm.name = ''
  searchForm.account = ''
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
      const res = await api.post('/workloads/import', formData, {
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
    await api.delete(`/workloads/${row.id}`)
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
    const res = await api.delete(`/workloads/import/${batch}`)
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
    await ElMessageBox.confirm(`确定要删除 ${deleteDate.value} 的所有工作量记录吗？`, '提示', { type: 'warning' })
    deletingByDate.value = true
    const res = await api.delete('/workloads/by-date', { params: { date: deleteDate.value } })
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