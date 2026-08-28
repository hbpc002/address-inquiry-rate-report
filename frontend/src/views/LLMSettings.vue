<template>
  <div class="llm-settings">
    <el-card class="section" shadow="never">
      <template #header>模型提供商</template>
      <div class="toolbar">
        <span class="tip">添加任意 OpenAI 兼容接口（DeepSeek / Qwen / Ollama 等），数据敏感时可指向本地 Ollama。</span>
        <el-button type="primary" size="small" @click="openCreate">新增提供商</el-button>
      </div>
      <el-table :data="providers" border size="small">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="base_url" label="Base URL" />
        <el-table-column prop="model" label="模型" />
        <el-table-column label="默认">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success">默认</el-tag>
            <el-button v-else link type="primary" size="small" @click="setDefault(row)">设为默认</el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="testProvider(row)">测试</el-button>
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="removeProvider(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="section" shadow="never">
      <template #header>悬浮按钮（智能体入口）自定义</template>
      <el-form :model="launcher" label-width="110px" size="small" style="max-width:560px">
        <el-form-item label="启用">
          <el-switch v-model="launcher.enabled" />
        </el-form-item>
        <el-form-item label="按钮文字">
          <el-input v-model="launcher.label" placeholder="如：智能助手" />
        </el-form-item>
        <el-form-item label="图标类型">
          <el-radio-group v-model="launcher.icon_type">
            <el-radio value="emoji">Emoji</el-radio>
            <el-radio value="url">图片URL</el-radio>
            <el-radio value="svg">SVG 代码</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="图标内容">
          <el-input
            v-model="launcher.icon_value"
            :placeholder="launcher.icon_type === 'emoji' ? '🤖' : launcher.icon_type === 'url' ? 'https://.../icon.png' : '<svg>...</svg>'"
          />
        </el-form-item>
        <el-form-item label="上传图标">
          <el-button size="small" @click="pickIcon">选择图片</el-button>
          <input ref="iconInput" type="file" accept="image/*" style="display:none" @change="onIconPicked" />
          <img v-if="launcher.icon_type === 'url' && launcher.icon_value" :src="launcher.icon_value" class="icon-preview" alt="" />
          <span class="tip" style="margin-left:8px">支持 png/jpg/gif/svg/webp，≤2MB；上传后自动填入上方图标内容</span>
        </el-form-item>
        <el-form-item label="位置">
          <el-radio-group v-model="launcher.position">
            <el-radio value="bottom-right">右下角</el-radio>
            <el-radio value="bottom-left">左下角</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="launcher.color" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveLauncher">保存界面配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑提供商' : '新增提供商'" width="520px">
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" :disabled="!!editing" />
        </el-form-item>
        <el-form-item label="Base URL" required>
          <el-input v-model="form.base_url" placeholder="https://api.openai.com/v1 或 http://host:11434/v1" />
        </el-form-item>
        <el-form-item label="模型" required>
          <el-input v-model="form.model" placeholder="如 qwen2.5:72b / deepseek-chat" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password :placeholder="editing ? '留空则不修改' : '可选，本地模型可空'" />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="dialogVisible = false">取消</el-button>
        <el-button size="small" @click="testForm">测试连接</el-button>
        <el-button type="primary" size="small" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/stores/user'
import { useLauncherStore } from '@/stores/launcher'

const launcherStore = useLauncherStore()

const providers = ref([])
const dialogVisible = ref(false)
const editing = ref(false)
const iconInput = ref(null)
const form = ref({ id: null, name: '', base_url: '', model: '', api_key: '', is_default: false })
const launcher = ref({ enabled: true, label: '智能助手', icon_type: 'emoji', icon_value: '🤖', position: 'bottom-right', color: '#409EFF', draggable: true, pos_x: null, pos_y: null })

async function loadProviders() {
  const r = await api.get('/llm-providers')
  providers.value = r.data || []
}
async function loadLauncher() {
  try {
    const r = await api.get('/llm-providers/launcher')
    if (r.data) launcher.value = { ...launcher.value, ...r.data }
  } catch (e) { /* default */ }
}

function openCreate() {
  editing.value = false
  form.value = { id: null, name: '', base_url: '', model: '', api_key: '', is_default: false }
  dialogVisible.value = true
}
function openEdit(row) {
  editing.value = true
  form.value = { id: row.id, name: row.name, base_url: row.base_url, model: row.model, api_key: '', is_default: row.is_default }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.name || !form.value.base_url || !form.value.model) {
    ElMessage.warning('名称 / Base URL / 模型 为必填')
    return
  }
  const payload = {
    name: form.value.name, base_url: form.value.base_url, model: form.value.model, is_default: form.value.is_default,
  }
  if (form.value.api_key) payload.api_key = form.value.api_key
  if (editing.value) {
    await api.put(`/llm-providers/${form.value.id}`, payload)
  } else {
    await api.post('/llm-providers', payload)
  }
  ElMessage.success('已保存')
  dialogVisible.value = false
  loadProviders()
}
async function removeProvider(row) {
  await ElMessageBox.confirm(`确认删除提供商「${row.name}」？`, '提示', { type: 'warning' })
  await api.delete(`/llm-providers/${row.id}`)
  ElMessage.success('已删除')
  loadProviders()
}
async function setDefault(row) {
  await api.put(`/llm-providers/${row.id}`, { name: row.name, base_url: row.base_url, model: row.model, is_default: true })
  if (row.api_key_masked) { /* 编辑时才需要 key，这里仅切换默认，沿用服务端 */ }
  ElMessage.success('已设为默认')
  loadProviders()
}
async function testProvider(row) {
  const r = await api.post('/llm-providers/test', { id: row.id })
  if (r.data.ok) ElMessage.success('连接成功：' + (r.data.sample || ''))
  else ElMessage.error('连接失败：' + (r.data.error || ''))
}
async function testForm() {
  if (!form.value.base_url || !form.value.model) { ElMessage.warning('请先填写 Base URL 与模型'); return }
  const payload = { base_url: form.value.base_url, model: form.value.model }
  if (form.value.api_key) payload.api_key = form.value.api_key
  if (editing.value) payload.id = form.value.id
  const r = await api.post('/llm-providers/test', payload)
  if (r.data.ok) ElMessage.success('连接成功：' + (r.data.sample || ''))
  else ElMessage.error('连接失败：' + (r.data.error || ''))
}
async function saveLauncher() {
  await api.put('/llm-providers/launcher', launcher.value)
  launcherStore.setConfig(launcher.value)
  ElMessage.success('已保存入口配置')
}

function pickIcon() {
  iconInput.value?.click()
}
async function onIconPicked(e) {
  const file = e.target.files && e.target.files[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    const r = await api.post('/llm-providers/launcher/icon', fd)
    launcher.value.icon_type = 'url'
    launcher.value.icon_value = r.data.url
    launcherStore.setConfig({ icon_type: 'url', icon_value: r.data.url })
    ElMessage.success('图标已上传，记得保存入口配置')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '上传失败')
  } finally {
    e.target.value = ''
  }
}

onMounted(() => { loadProviders(); loadLauncher() })
</script>

<style scoped>
.llm-settings { padding: 16px; }
.section { margin-bottom: 16px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.tip { color: #909399; font-size: 13px; }
.icon-preview { width: 32px; height: 32px; object-fit: contain; margin-left: 8px; vertical-align: middle; border-radius: 6px; border: 1px solid #ebeef5; }
</style>
