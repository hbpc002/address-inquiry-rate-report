<template>
  <div class="agent-chat">
    <div class="agent-header">
      <div class="title">智能体 · 自然语言查报表</div>
      <div class="header-right">
        <el-select
          v-if="providers.length"
          v-model="store.provider"
          size="small"
          placeholder="提供商"
          style="width: 130px"
          @change="onProviderChange"
        >
          <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.name" />
        </el-select>
        <el-select
          v-if="currentModels.length"
          v-model="store.model"
          size="small"
          placeholder="模型"
          style="width: 150px"
        >
          <el-option v-for="m in currentModels" :key="m" :label="m" :value="m" />
        </el-select>
        <el-button size="small" text @click="store.clear()">清空</el-button>
      </div>
    </div>

    <div class="messages" ref="messagesRef">
      <div v-if="!store.bubbleItems.length" class="empty">
        <Prompts :items="promptItems" :wrap="true" @itemClick="onPrompt" />
      </div>

      <BubbleList v-else :list="store.bubbleItems" :auto-scroll="true" class="bubble-list">
        <template #content="{ item }">
          <div class="bubble-body">
            <ThoughtChain
              v-if="item.thoughtItems && item.thoughtItems.length"
              :thinking-items="item.thoughtItems"
              class="thought-chain"
            />
            <MarkdownMessage v-if="item.placement === 'start'" :content="item.content" />
            <span v-else class="user-text">{{ item.content }}</span>
          </div>
        </template>
      </BubbleList>
    </div>

    <div class="input-bar">
      <el-input
        v-model="store.input"
        type="textarea"
        :rows="2"
        resize="none"
        placeholder="输入问题，Enter 发送 / Shift+Enter 换行"
        @keydown.enter.exact.prevent="send()"
      />
      <el-button v-if="!store.streaming" type="primary" :disabled="!store.input.trim()" @click="send()">发送</el-button>
      <el-button v-else type="danger" @click="store.stop()">停止</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import { BubbleList, ThoughtChain, Prompts } from 'vue-element-plus-x'
import { api } from '@/stores/user'
import { useAgentChatStore } from '@/stores/agentChat'
import MarkdownMessage from '@/components/MarkdownMessage.vue'

defineProps({
  embedded: { type: Boolean, default: false },
})

const store = useAgentChatStore()
const messagesRef = ref(null)
const providers = ref([])

const currentModels = computed(() => {
  const p = providers.value.find((x) => x.name === store.provider)
  return p && Array.isArray(p.models) ? p.models.map((m) => (typeof m === 'string' ? m : m.model)) : []
})

const suggestions = [
  '2026-07 各班组出勤率排名',
  '最近一周谁工时最低',
  '导出 7 月考勤报表',
  '本月迟到次数最多的人',
]
const promptItems = suggestions.map((label, i) => ({ key: String(i), label }))

function scrollBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

function onPrompt(item) {
  if (item && item.label) store.send(item.label)
}

function send(text) {
  store.send(text)
  scrollBottom()
}

function onProviderChange() {
  store.model = ''
}

async function loadProviders() {
  try {
    const r = await api.get('/llm-providers')
    providers.value = r.data || []
    if (!store.provider && providers.value.length) {
      const def = providers.value.find((p) => p.is_default) || providers.value[0]
      store.provider = def.name
    }
  } catch (e) {
    /* 无权限或接口异常时不影响对话 */
  }
}

onMounted(() => {
  loadProviders()
  scrollBottom()
})
</script>

<style scoped>
.agent-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 420px;
}
.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #ebeef5;
}
.title { font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 8px; }
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f7f8fa;
}
.empty { text-align: center; color: #909399; margin-top: 40px; }
.bubble-list { background: transparent; }
.bubble-body { word-break: break-word; }
.user-text { white-space: pre-wrap; }
.thought-chain { margin-bottom: 8px; }
.input-bar {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid #ebeef5;
  align-items: flex-end;
}
.input-bar .el-input { flex: 1; }
</style>
