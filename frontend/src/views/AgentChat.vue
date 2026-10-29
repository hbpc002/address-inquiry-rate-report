<template>
  <div class="agent-chat" :class="{ 'is-embedded': embedded }">
    <AgentConversations
      v-if="showConversations"
      :conversations="store.conversations"
      :active-id="store.conversationId"
      :loading="store.conversationsLoading"
      :search="store.conversationSearch"
      :total="store.conversationsTotal"
      :show-owner="isAdmin"
      @new="newChat"
      @select="selectConversation"
      @search="onSearch"
      @rename="renameConversation"
      @pin="pinConversation"
      @delete="deleteConversation"
      @close="showConversations = false"
    />
    <div
      v-if="showConversations"
      class="sidebar-backdrop"
      @click="showConversations = false"
    ></div>

    <div class="agent-main">
      <header class="agent-topbar">
        <div class="agent-identity">
          <button
            type="button"
            class="sidebar-toggle"
            title="会话列表"
            aria-label="会话列表"
            @click="showConversations = !showConversations"
          >
            ☰
          </button>
          <AgentAvatar
            :type="agentIcon.type"
            :value="agentIcon.value"
            :color="agentIcon.color"
            :offset-x="agentIcon.offsetX"
            :offset-y="agentIcon.offsetY"
            :scale="agentIcon.scale"
            :size="34"
          />
          <div class="agent-identity-text">
            <div class="agent-title">{{ agentName }}</div>
            <div class="agent-subtitle">
              {{ store.conversationTitle || '考勤 · 工时 · 排班 · 运营数据' }}
            </div>
          </div>
        </div>
        <div class="agent-top-actions">
          <button
            type="button"
            class="thinking-toggle"
            :class="{ active: store.showThinking }"
            :aria-pressed="store.showThinking"
            :title="store.showThinking ? '隐藏思考过程' : '显示思考过程'"
            @click="store.showThinking = !store.showThinking"
          >✦ 思考</button>
          <span class="agent-status" :class="{ live: store.streaming }">
            <span class="status-dot" aria-hidden="true"></span>
            {{ store.streaming ? '生成中' : '在线' }}
          </span>
          <button type="button" class="clear-button" @click="newChat">新对话</button>
        </div>
      </header>

      <div ref="messagesRef" class="agent-transcript" @scroll.passive="onMessagesScroll">
        <div v-if="!store.bubbleItems.length" class="agent-empty">
          <AgentAvatar
            :type="agentIcon.type"
            :value="agentIcon.value"
            :color="agentIcon.color"
            :offset-x="agentIcon.offsetX"
            :offset-y="agentIcon.offsetY"
            :scale="agentIcon.scale"
            :size="62"
          />
          <h1>今天想查什么？</h1>
          <p>用自然语言查询考勤、工时、排班、工作量、营销和宽带订单</p>
          <div class="suggestion-grid">
            <button
              v-for="item in promptItems"
              :key="item.key"
              type="button"
              class="suggestion-card"
              @click="onPrompt(item)"
            >
              <span class="suggestion-arrow" aria-hidden="true">↗</span>
              <span>{{ item.label }}</span>
            </button>
          </div>
        </div>

        <div v-else class="turns">
          <template v-for="item in store.bubbleItems" :key="item.id">
            <AgentUserMessage v-if="item.placement === 'end'" :message="item" />
            <AgentReply
              v-else
              :message="item"
              :agent-name="agentName"
              :agent-icon="agentIcon"
              :show-thinking="store.showThinking"
            />
          </template>
        </div>
      </div>

      <Transition name="jump-fade">
        <button v-if="showJump" type="button" class="jump-latest" @click="scrollBottom">
          回到最新 ↓
        </button>
      </Transition>

      <AgentComposer
        v-model="store.input"
        :streaming="store.streaming"
        :providers="providers"
        :models="currentModels"
        :provider="store.provider"
        :model="store.model"
        :suggestions="suggestions"
        @update:provider="onProviderChange"
        @update:model="store.model = $event"
        @send="send()"
        @stop="store.stop()"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/stores/user'
import { useAgentChatStore } from '@/stores/agentChat'
import { useLauncherStore } from '@/stores/launcher'
import { useUserStore } from '@/stores/user'
import AgentUserMessage from '@/components/AgentUserMessage.vue'
import AgentReply from '@/components/AgentReply.vue'
import AgentComposer from '@/components/AgentComposer.vue'
import AgentAvatar from '@/components/AgentAvatar.vue'
import AgentConversations from '@/components/AgentConversations.vue'

const props = defineProps({
  embedded: { type: Boolean, default: false },
})

const store = useAgentChatStore()
const launcher = useLauncherStore()
const userStore = useUserStore()
const messagesRef = ref(null)
const providers = ref([])
const showJump = ref(false)
const showConversations = ref(!props.embedded && window.innerWidth > 820)
let searchTimer = null

const isAdmin = computed(
  () => userStore.isSystem || userStore.user?.role === 'admin'
)

const agentName = computed(() => launcher.config.label || '数据智能体')
const agentIcon = computed(() => ({
  type: launcher.config.icon_type || 'emoji',
  value: launcher.config.icon_value || '🤖',
  color: launcher.config.color || '#5b6ee1',
  offsetX: Number(launcher.config.icon_offset_x) || 0,
  offsetY: Number(launcher.config.icon_offset_y) || 0,
  scale: Number(launcher.config.icon_scale) || 100,
}))

const currentModels = computed(() => {
  const p = providers.value.find((x) => x.name === store.provider)
  return p && Array.isArray(p.models)
    ? p.models.map((m) => (typeof m === 'string' ? m : m.model))
    : []
})

const DEFAULT_SUGGESTIONS = [
  '2026-07 各班组出勤率排名',
  '最近一周谁工时最低',
  '本月迟到次数最多的人',
  '2026-07 每天实际工时趋势',
]
const suggestions = ref([...DEFAULT_SUGGESTIONS])
const promptItems = computed(() =>
  suggestions.value.map((label, i) => ({ key: String(i), label }))
)

function scrollBottom() {
  stickToBottom = true
  showJump.value = false
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

function onPrompt(item) {
  if (item && item.label) send(item.label)
}

function send(text) {
  const question = text != null ? text : store.input
  if (!String(question || '').trim() || store.streaming) return
  stickToBottom = true
  showJump.value = false
  store.send(question)
  scrollBottom()
}

function onProviderChange(value) {
  store.provider = value
  store.model = ''
}

function newChat() {
  store.newConversation()
  showJump.value = false
  if (window.innerWidth <= 820) showConversations.value = false
  scrollBottom()
}

async function selectConversation(id) {
  if (store.streaming) store.stop()
  try {
    await store.loadConversation(id)
    showJump.value = false
    scrollBottom()
    if (window.innerWidth <= 820) showConversations.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载会话失败')
  }
}

function onSearch(value) {
  store.conversationSearch = value
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.loadConversations(value)
  }, 300)
}

async function renameConversation(item) {
  try {
    const result = await ElMessageBox.prompt('请输入新的会话标题', '重命名会话', {
      inputValue: item.title || '新对话',
      inputPattern: /\S+/,
      inputErrorMessage: '标题不能为空',
    })
    await store.renameConversation(item.id, result.value.trim())
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.response?.data?.detail || '重命名失败')
    }
  }
}

async function pinConversation(item) {
  try {
    await store.togglePin(item.id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function deleteConversation(item) {
  try {
    await ElMessageBox.confirm(`确定删除会话「${item.title || '新对话'}」吗？`, '删除会话', {
      type: 'warning',
    })
    await store.deleteConversation(item.id)
    ElMessage.success('会话已删除')
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

let scrollScheduled = false
let stickToBottom = true

function onMessagesScroll() {
  const el = messagesRef.value
  if (!el) return
  stickToBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
  showJump.value = !stickToBottom && store.bubbleItems.length > 0
}

function scheduleScroll() {
  if (!stickToBottom || scrollScheduled) return
  scrollScheduled = true
  requestAnimationFrame(() => {
    scrollScheduled = false
    scrollBottom()
  })
}

watch(() => store.bubbleItems, scheduleScroll, { deep: true })

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

async function loadSuggestions() {
  try {
    const r = await api.get('/agent-settings')
    if (r.data && Array.isArray(r.data.suggestions) && r.data.suggestions.length) {
      suggestions.value = r.data.suggestions
    }
  } catch (e) {
    /* 失败时使用默认快捷问题 */
  }
}

async function initialize() {
  store.activate()
  if (!launcher.loaded) launcher.load()
  await Promise.all([loadProviders(), loadSuggestions(), store.loadConversations()])
  if (store.conversationId) {
    try {
      await store.loadConversation(store.conversationId)
    } catch (e) {
      store.newConversation()
    }
  }
  scrollBottom()
}

onMounted(initialize)
onUnmounted(() => clearTimeout(searchTimer))
</script>

<style scoped>
.agent-chat {
  --agent-bg: #f6f5f2;
  --agent-panel: #fffdf9;
  --agent-user-card: #fffdf9;
  --agent-raised: #f0efeb;
  --agent-hover: #f1f0ec;
  --agent-line: rgba(31, 32, 38, 0.09);
  --agent-line-strong: rgba(31, 32, 38, 0.14);
  --agent-text: #1f2026;
  --agent-muted: #6f7280;
  --agent-faint: #a3a4ad;
  --agent-accent: #5b6ee1;
  --agent-accent-strong: #485bd6;
  --agent-accent-soft: #eef0ff;
  --agent-accent-line: rgba(91, 110, 225, 0.38);
  --agent-ok: #5f8f4e;
  --agent-ok-soft: #edf6e8;
  --agent-warn: #b7791f;
  --agent-warn-soft: #fbf3e2;
  --agent-err: #c25566;
  --agent-err-soft: #fdeef1;
  --agent-radius: 10px;
  --agent-radius-lg: 14px;
  position: relative;
  display: flex;
  flex-direction: row;
  height: 100%;
  min-height: 520px;
  background: var(--agent-bg);
  color: var(--agent-text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.agent-main {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  height: 100%;
}
.sidebar-backdrop {
  display: none;
}
.agent-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--agent-line);
  background: color-mix(in srgb, var(--agent-bg) 88%, #fff);
  flex: none;
}
.agent-identity {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.sidebar-toggle {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--agent-line);
  border-radius: 9px;
  background: var(--agent-panel);
  color: var(--agent-muted);
  font-size: 15px;
  cursor: pointer;
  flex: none;
}
.sidebar-toggle:hover {
  color: var(--agent-text);
  background: var(--agent-hover);
}
.agent-identity-text {
  min-width: 0;
}
.agent-title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.01em;
}
.agent-subtitle {
  margin-top: 1px;
  color: var(--agent-muted);
  font-size: 11.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.agent-top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}
.agent-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--agent-line);
  border-radius: 999px;
  background: var(--agent-panel);
  color: var(--agent-muted);
  font-size: 11.5px;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--agent-ok);
  box-shadow: 0 0 0 3px var(--agent-ok-soft);
}
.agent-status.live .status-dot {
  background: var(--agent-accent);
  box-shadow: 0 0 0 3px var(--agent-accent-soft);
  animation: agent-status-pulse 1.4s ease-out infinite;
}
.thinking-toggle {
  height: 26px;
  padding: 0 9px;
  border: 1px solid var(--agent-line);
  border-radius: 999px;
  background: var(--agent-panel);
  color: var(--agent-muted);
  font-size: 11.5px;
  cursor: pointer;
  transition: background-color 0.14s ease, border-color 0.14s ease, color 0.14s ease;
}
.thinking-toggle:hover {
  background: var(--agent-hover);
  color: var(--agent-text);
}
.thinking-toggle.active {
  border-color: var(--agent-accent-line);
  background: var(--agent-accent-soft);
  color: var(--agent-accent-strong);
}
.clear-button {
  height: 28px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--agent-muted);
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.14s ease, color 0.14s ease;
}
.clear-button:hover {
  background: var(--agent-hover);
  color: var(--agent-text);
}
.agent-transcript {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 20px 8px;
  scrollbar-gutter: stable;
}
.turns {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
}
.agent-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 760px;
  margin: 6vh auto 0;
  padding: 24px 8px 40px;
  text-align: center;
}
.agent-empty h1 {
  margin: 18px 0 6px;
  font-size: 27px;
  line-height: 1.25;
  letter-spacing: -0.02em;
}
.agent-empty p {
  max-width: 480px;
  margin: 0;
  color: var(--agent-muted);
  font-size: 13.5px;
  line-height: 1.65;
}
.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
  max-width: 660px;
  margin-top: 26px;
}
.suggestion-card {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  min-height: 58px;
  padding: 13px 14px;
  border: 1px solid var(--agent-line);
  border-radius: var(--agent-radius-lg);
  background: var(--agent-panel);
  color: var(--agent-text);
  font-size: 13px;
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}
.suggestion-card:hover {
  background: #fff;
  border-color: var(--agent-accent-line);
  transform: translateY(-1px);
}
.suggestion-arrow {
  color: var(--agent-accent);
  font-size: 15px;
  line-height: 1.2;
  flex: none;
}
.jump-latest {
  position: absolute;
  left: 50%;
  bottom: 98px;
  z-index: 2;
  transform: translateX(-50%);
  padding: 7px 13px;
  border: 1px solid var(--agent-line);
  border-radius: 999px;
  background: var(--agent-panel);
  color: var(--agent-muted);
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 10px 24px -16px rgba(31, 32, 38, 0.4);
}
.jump-latest:hover {
  color: var(--agent-text);
}
.jump-fade-enter-active,
.jump-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.jump-fade-enter-from,
.jump-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 4px);
}
.agent-chat.is-embedded .agent-topbar {
  padding: 10px 14px;
}
.agent-chat.is-embedded .agent-transcript {
  padding: 16px 14px 6px;
}
.agent-chat.is-embedded .turns {
  gap: 15px;
}
@keyframes agent-status-pulse {
  0% { box-shadow: 0 0 0 0 var(--agent-accent-soft); }
  70% { box-shadow: 0 0 0 6px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}
@media (max-width: 820px) {
  .agent-chat {
    min-height: 100%;
  }
  .sidebar-backdrop {
    position: absolute;
    inset: 0;
    z-index: 15;
    display: block;
    background: rgba(31, 32, 38, 0.24);
  }
  .agent-topbar {
    padding: 10px 14px;
  }
  .agent-subtitle {
    display: none;
  }
  .agent-transcript {
    padding: 16px 12px 4px;
  }
  .turns {
    gap: 16px;
  }
  .agent-empty {
    margin-top: 4vh;
    padding-inline: 0;
  }
  .agent-empty h1 {
    font-size: 23px;
  }
  .suggestion-grid {
    grid-template-columns: 1fr;
    margin-top: 20px;
  }
  .suggestion-card {
    min-height: 52px;
  }
  .jump-latest {
    bottom: 88px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .status-dot,
  .suggestion-card,
  .jump-fade-enter-active,
  .jump-fade-leave-active {
    animation: none;
    transition: none;
  }
}
</style>
