<template>
  <div class="work-hour-settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>工时预警阈值设置</span>
          <el-button type="primary" @click="handleAdd">新增阈值</el-button>
        </div>
      </template>

      <el-alert
        title="说明"
        type="info"
        :closable="false"
        style="margin-bottom: 15px"
      >
        <template #default>
          工时异常判定基于班组平均工时：
          <br>• 超时：工时 ≥ 班组平均 × 超时倍率
          <br>• 过短：工时 ≤ 班组平均 × 过短倍率
          <br>• 岗位为"组长"或"师傅"的员工不参与异常判定
        </template>
      </el-alert>

      <el-table :data="tableData" border stripe>
        <el-table-column prop="team" label="班组" width="150" />
        <el-table-column label="超时倍率" width="120">
          <template #default="{ row }">
            <el-input-number
              v-if="row.editing"
              v-model="row.edit_overtime"
              :min="1.0"
              :max="2.0"
              :step="0.1"
              size="small"
              style="width: 80px"
            />
            <span v-else>{{ row.overtime_ratio }}x</span>
          </template>
        </el-table-column>
        <el-table-column label="过短倍率" width="120">
          <template #default="{ row }">
            <el-input-number
              v-if="row.editing"
              v-model="row.edit_undertime"
              :min="0.1"
              :max="1.0"
              :step="0.1"
              size="small"
              style="width: 80px"
            />
            <span v-else>{{ row.undertime_ratio }}x</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.has_threshold ? 'success' : 'info'">
              {{ row.has_threshold ? '已配置' : '默认' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <template v-if="row.editing">
              <el-button type="primary" link @click="handleSave(row)">保存</el-button>
              <el-button link @click="handleCancel(row)">取消</el-button>
            </template>
            <template v-else>
              <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
              <el-button type="danger" link @click="handleDelete(row)" v-if="row.has_threshold">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增阈值" width="400px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="班组">
          <el-select v-model="form.team" placeholder="选择班组" filterable style="width: 100%">
            <el-option
              v-for="t in availableTeams"
              :key="t.team"
              :label="t.team"
              :value="t.team"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="超时倍率">
          <el-input-number v-model="form.overtime_ratio" :min="1.0" :max="2.0" :step="0.1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="过短倍率">
          <el-input-number v-model="form.undertime_ratio" :min="0.1" :max="1.0" :step="0.1" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'

const tableData = ref([])
const dialogVisible = ref(false)
const form = ref({
  team: '',
  overtime_ratio: 1.2,
  undertime_ratio: 0.8
})
const availableTeams = ref([])

async function loadData() {
  try {
    const [teamsRes, thresholdsRes] = await Promise.all([
      api.get('/work-hour-thresholds/teams'),
      api.get('/work-hour-thresholds')
    ])
    
    const thresholdMap = {}
    thresholdsRes.data.forEach(t => {
      thresholdMap[t.team] = t
    })
    
    tableData.value = teamsRes.data.map(t => {
      const threshold = thresholdMap[t.team]
      return {
        team: t.team,
        overtime_ratio: threshold ? threshold.overtime_ratio : t.overtime_ratio,
        undertime_ratio: threshold ? threshold.undertime_ratio : t.undertime_ratio,
        has_threshold: !!threshold,
        editing: false,
        edit_overtime: threshold ? threshold.overtime_ratio : t.overtime_ratio,
        edit_undertime: threshold ? threshold.undertime_ratio : t.undertime_ratio,
        id: threshold ? threshold.id : null
      }
    })
    availableTeams.value = teamsRes.data
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

function handleAdd() {
  const configuredTeams = tableData.value.filter(t => t.has_threshold).map(t => t.team)
  const unconfigured = availableTeams.value.filter(t => !configuredTeams.includes(t.team))
  
  if (unconfigured.length === 0) {
    ElMessage.warning('所有班组已配置阈值')
    return
  }
  
  form.value = {
    team: unconfigured[0].team,
    overtime_ratio: 1.2,
    undertime_ratio: 0.8
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    await api.post('/work-hour-thresholds', {
      team: form.value.team,
      overtime_ratio: form.value.overtime_ratio,
      undertime_ratio: form.value.undertime_ratio
    })
    ElMessage.success('添加成功')
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  }
}

function handleEdit(row) {
  row.editing = true
  row.edit_overtime = row.overtime_ratio
  row.edit_undertime = row.undertime_ratio
}

function handleCancel(row) {
  row.editing = false
}

async function handleSave(row) {
  try {
    await api.put(`/work-hour-thresholds/${row.id}`, {
      overtime_ratio: row.edit_overtime,
      undertime_ratio: row.edit_undertime
    })
    ElMessage.success('更新成功')
    row.editing = false
    row.overtime_ratio = row.edit_overtime
    row.undertime_ratio = row.edit_undertime
    loadData()
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

async function handleDelete(row) {
  try {
    await api.delete(`/work-hour-thresholds/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    ElMessage.error('删除失败')
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