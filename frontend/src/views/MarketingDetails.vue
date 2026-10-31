<template>
  <div class="marketing-details">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.marketing_orders }}</span>
          <div>
            <el-button v-if="userStore.hasPermission('marketing.export')" type="success" @click="handleExport">导出营销明细</el-button>
            <el-button v-if="userStore.hasPermission('marketing.upload')" type="primary" @click="dialogVisible = true">导入营销明细</el-button>
          </div>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="竣工日期">
          <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" style="width: 240px" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="searchForm.kf_id" placeholder="客服工号" clearable style="width: 130px" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="员工姓名" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="组织">
          <el-input v-model="searchForm.org_name" placeholder="组织关键词" clearable style="width: 150px" />
        </el-form-item>
        <el-form-item label="数据来源">
          <el-select v-model="searchForm.data_type" placeholder="全部来源" clearable style="width: 120px">
            <el-option label="线上直办" value="xszb" />
            <el-option label="办理工单" value="fwgd" />
          </el-select>
        </el-form-item>
        <el-form-item label="产品">
          <el-input v-model="searchForm.product" placeholder="产品ID/名称" clearable style="width: 140px" />
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
        <el-button v-if="userStore.hasPermission('marketing.delete')" type="danger" @click="deleteByDateVisible = true">按日期删除</el-button>
        <el-button v-if="userStore.hasPermission('marketing.delete')" type="danger" :disabled="!searchForm.batch" @click="handleDeleteBatch">按批次删除</el-button>
      </el-space>

      <el-table :data="tableData" border stripe max-height="calc(100vh - 360px)">
        <el-table-column prop="finish_date" label="竣工日期" width="105" />
        <el-table-column prop="source" label="数据来源" width="95" />
        <el-table-column prop="kf_id" label="客服工号" width="120" />
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column prop="team" label="班组" min-width="120" />
        <el-table-column prop="group_name" label="行分类" width="150" />
        <el-table-column prop="org_name" label="组织机构" min-width="200" show-overflow-tooltip />
        <el-table-column prop="tenant" label="建单租户" width="110" show-overflow-tooltip />
        <el-table-column prop="work_order_id" label="工单流水号" width="160" show-overflow-tooltip />
        <el-table-column prop="trade_id" label="CBSS订单号" width="150" />
        <el-table-column prop="service_type" label="重点业务" width="90" />
        <el-table-column prop="valid_type" label="叠加包有效期" width="105" />
        <el-table-column prop="product_id" label="产品ID" width="100" />
        <el-table-column prop="product_name" label="产品名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="lh_qh" label="来话/去话" width="90" />
        <el-table-column prop="channel" label="受理渠道" width="95" />
        <el-table-column prop="area_name" label="地市" width="80" />
        <el-table-column prop="import_batch" label="批次" width="90" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button v-if="userStore.hasPermission('marketing.delete')" type="danger" link @click="handleDelete(row)">删除</el-button>
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

    <el-dialog v-if="userStore.hasPermission('marketing.upload')" v-model="dialogVisible" title="导入营销明细" width="540px" @closed="closeDialog">
      <el-upload
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
          <div class="el-upload__tip">自动识别线上直办/办理工单文件；同来源、同竣工日期数据会被覆盖</div>
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

    <el-dialog v-model="deleteByDateVisible" title="按竣工日期删除" width="360px">
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
const searchForm = reactive({ batch: '', kf_id: '', name: '', org_name: '', data_type: '', product: '' })
const range = ref('')
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const fileList = ref([])
const uploadResults = ref([])

function buildSearchParams() {
  const params = {
    import_batch: searchForm.batch || undefined,
    kf_id: searchForm.kf_id || undefined,
    name: searchForm.name || undefined,
    org_name: searchForm.org_name || undefined,
    data_type: searchForm.data_type || undefined,
    product: searchForm.product || undefined
  }
  if (range.value && range.value.length === 2) {
    params.start_date = range.value[0]
    params.end_date = range.value[1]
  }
  return params
}

async function loadData() {
  try {
    const params = {
      ...buildSearchParams(),
      page: pagination.page,
      limit: pagination.limit
    }
    const res = await api.get('/marketing/details', { params })
    tableData.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

function handleExport() {
  downloadBlob('/marketing/details/export', buildSearchParams(), '营销明细.csv')
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

function resetSearch() {
  searchForm.batch = ''
  searchForm.kf_id = ''
  searchForm.name = ''
  searchForm.org_name = ''
  searchForm.data_type = ''
  searchForm.product = ''
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
      const res = await api.post('/marketing/details/import', formData, {
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
    await ElMessageBox.confirm('确定要删除该营销明细吗?', '提示', { type: 'warning' })
    await api.delete(`/marketing/details/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function handleDeleteBatch() {
  if (!searchForm.batch) return
  try {
    await ElMessageBox.confirm(`确定要删除批次 "${searchForm.batch}" 的所有记录吗？`, '提示', { type: 'warning' })
    const res = await api.delete(`/marketing/details/import/${searchForm.batch}`)
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
    await ElMessageBox.confirm(`确定要删除 ${deleteDate.value} 的所有营销明细吗？`, '提示', { type: 'warning' })
    deletingByDate.value = true
    const res = await api.delete('/marketing/details/by-date', { params: { date: deleteDate.value } })
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
