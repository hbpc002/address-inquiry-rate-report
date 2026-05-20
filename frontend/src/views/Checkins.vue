<template>
  <div class="checkins">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>签到记录</span>
          <el-button v-if="userStore.hasPermission('upload_checkin')" type="primary" @click="dialogVisible = true">导入签到</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="导入批次">
          <el-input v-model="searchForm.batch" placeholder="批次号" clearable />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="searchForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" border stripe>
        <el-table-column prop="emp_no" label="工号" width="100" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="checkin_time" label="签到时间" width="180">
          <template #default="{ row }">
            {{ row.checkin_time?.slice(0, 19) }}
          </template>
        </el-table-column>
        <el-table-column prop="checkout_time" label="签退时间" width="180">
          <template #default="{ row }">
            {{ row.checkout_time?.slice(0, 19) }}
          </template>
        </el-table-column>
        <el-table-column prop="device_no" label="设备号" width="100" />
        <el-table-column prop="dept" label="部门" width="120" />
        <el-table-column prop="import_batch" label="批次号" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button v-if="userStore.canEdit()" type="danger" link @click="handleDelete(row)">删除</el-button>
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

    <el-dialog v-if="userStore.hasPermission('upload_checkin')" v-model="dialogVisible" title="导入签到记录" width="400px">
      <el-upload
        ref="upload"
        :auto-upload="false"
        :limit="1"
        accept=".csv"
        :on-change="handleFileChange"
      >
        <el-button type="primary">选择CSV文件</el-button>
        <template #tip>
          <div class="el-upload__tip">支持CSV格式，第一行必须包含表头：工号,姓名,签到时间,签退时间,设备号,归属部门</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api, useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'

const userStore = useUserStore()
const tableData = ref([])
const dialogVisible = ref(false)
const uploading = ref(false)
const searchForm = reactive({ batch: '', date: '' })
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const uploadFile = ref(null)

async function loadData() {
  try {
    const params = {
      page: pagination.page,
      limit: pagination.limit,
      import_batch: searchForm.batch || undefined,
      checkin_date: searchForm.date || undefined
    }
    const res = await api.get('/checkins', { params })
    tableData.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

function handleFileChange(file) {
  uploadFile.value = file.raw
}

async function handleUpload() {
  if (!uploadFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    const res = await api.post('/checkins/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success(`导入成功，共${res.data.count}条记录`)
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    uploading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该记录吗?', '提示', { type: 'warning' })
    await api.delete(`/checkins/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
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