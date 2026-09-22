<template>
  <div class="agent-settings">
    <el-card class="section" shadow="never">
      <template #header>系统提示词</template>
      <el-alert type="info" :closable="false" style="margin-bottom: 12px"
        title="可用占位符：{current_date} 当前日期、{data_range} 数据范围。修改后对新对话立即生效。" />
      <el-input
        v-model="form.system_prompt"
        type="textarea"
        :rows="16"
        placeholder="智能体系统提示词"
        style="font-family: monospace"
      />
    </el-card>

    <el-card class="section" shadow="never">
      <template #header>
        <div class="card-header">
          <span>快捷问题建议</span>
          <el-button size="small" @click="addSuggestion">添加</el-button>
        </div>
      </template>
      <div v-for="(item, idx) in form.suggestions" :key="idx" class="suggestion-row">
        <el-input v-model="form.suggestions[idx]" placeholder="如：本月迟到次数最多的人" />
        <el-button type="danger" link @click="removeSuggestion(idx)">删除</el-button>
      </div>
      <div v-if="!form.suggestions.length" class="tip">暂无快捷问题，点击右上角添加</div>
    </el-card>

    <el-card class="section" shadow="never">
      <template #header>运行参数</template>
      <el-form label-width="180px" size="small" style="max-width: 560px">
        <el-form-item label="最大工具循环次数">
          <el-input-number v-model="form.max_iterations" :min="1" :max="20" />
          <span class="tip">单轮对话内工具最多调用次数，默认 6</span>
        </el-form-item>
        <el-form-item label="历史消息条数">
          <el-input-number v-model="form.max_history_messages" :min="2" :max="100" />
          <span class="tip">发给模型的最近消息上限，默认 12</span>
        </el-form-item>
        <el-form-item label="连续SQL失败阈值">
          <el-input-number v-model="form.consecutive_run_sql_failures" :min="1" :max="10" />
          <span class="tip">连续失败多少次后改用报表工具，默认 2</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button @click="resetDefaults">恢复默认</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'

const saving = ref(false)
const form = reactive({
  system_prompt: '',
  suggestions: [],
  max_iterations: 6,
  max_history_messages: 12,
  consecutive_run_sql_failures: 2,
})

function apply(data) {
  form.system_prompt = data.system_prompt || ''
  form.suggestions = Array.isArray(data.suggestions) ? [...data.suggestions] : []
  form.max_iterations = data.max_iterations ?? 6
  form.max_history_messages = data.max_history_messages ?? 12
  form.consecutive_run_sql_failures = data.consecutive_run_sql_failures ?? 2
}

async function load() {
  try {
    const r = await api.get('/agent-settings')
    if (r.data) apply(r.data)
  } catch (e) {
    /* 使用默认值 */
  }
}

function addSuggestion() {
  form.suggestions.push('')
}
function removeSuggestion(idx) {
  form.suggestions.splice(idx, 1)
}

async function save() {
  if (!form.system_prompt.trim()) {
    ElMessage.warning('系统提示词不能为空')
    return
  }
  saving.value = true
  try {
    const r = await api.put('/agent-settings', {
      system_prompt: form.system_prompt,
      suggestions: form.suggestions.map(s => String(s).trim()).filter(Boolean),
      max_iterations: form.max_iterations,
      max_history_messages: form.max_history_messages,
      consecutive_run_sql_failures: form.consecutive_run_sql_failures,
    })
    apply(r.data)
    ElMessage.success('智能体设置已保存')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function resetDefaults() {
  try {
    await ElMessageBox.confirm('确定恢复为默认设置吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  saving.value = true
  try {
    const r = await api.post('/agent-settings/reset')
    apply(r.data)
    ElMessage.success('已恢复默认设置')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '恢复失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.agent-settings .section {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.suggestion-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}
.suggestion-row .el-input {
  flex: 1;
}
.tip {
  color: #909399;
  font-size: 12px;
  margin-left: 8px;
}
</style>
