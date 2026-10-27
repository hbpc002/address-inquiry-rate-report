<template>
  <div class="agent-chat" :class="{ 'is-embedded': embedded }">
    <header class="agent-topbar">
      <div class="agent-identity">
        <span class="agent-orb" aria-hidden="true">✦</span>
        <div class="agent-identity-text">
          <div class="agent-title">数据智能体</div>
          <div class="agent-subtitle">考勤 · 工时 · 排班 · 运营数据</div>
        </div>
      </div>
      <div class="agent-top-actions">
        <span class="agent-status" :class="{ live: store.streaming }">
          <span class="status-dot" aria-hidden="true"></span>
          {{ store.streaming ? '生成中' : '在线' }}
        </span>
        <button type="button" class="clear-button" @click="clearChat">清空</button>
      </div>
    </header>

    <div ref="messagesRef" class="agent-transcript" @scroll.passive="onMessagesScroll">
      <div v-if="!store.bubbleItems.length" class="agent-empty">
        <div class="empty-mark" aria-hidden="true">✦</div>
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
          <AgentReply v-else :message="item" />
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
      @update:provider="onProviderChange"
      @update:model="store.model = $event"
      @send="send()"
      @stop="store.stop()"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { api } from '@/stores/user'
import { useAgentChatStore } from '@/stores/agentChat'
import AgentUserMessage from '@/components/AgentUserMessage.vue'
import AgentReply from '@/components/AgentReply.vue'
import AgentComposer from '@/components/AgentComposer.vue'

defineProps({
  embedded: { type: Boolean, default: false },
})

const store = useAgentChatStore()
const messagesRef = ref(null)
const providers = ref([])
const showJump = ref(false)

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

function clearChat() {
  store.clear()
  showJump.value = false
  scrollBottom()
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

onMounted(() => {
  store.activate()
  loadProviders()
  loadSuggestions()
  scrollBottom()
})
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
  flex-direction: column;
  height: 100%;
  min-height: 520px;
  background: var(--agent-bg);
  color: var(--agent-text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
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
.agent-orb {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--agent-accent-line);
  border-radius: 50%;
  background: var(--agent-accent-soft);
  color: var(--agent-accent);
  font-size: 15px;
  flex: none;
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
.empty-mark {
  display: grid;
  place-items: center;
  width: 62px;
  height: 62px;
  border: 1px solid var(--agent-accent-line);
  border-radius: 22px;
  background: var(--agent-panel);
  color: var(--agent-accent);
  font-size: 27px;
  box-shadow: 0 18px 38px -26px rgba(31, 32, 38, 0.4);
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
@media (max-width: 699px) {
  .agent-chat {
    min-height: 100%;
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
  .empty-mark {
    width: 54px;
    height: 54px;
    border-radius: 18px;
    font-size: 23px;
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
