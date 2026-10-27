<template>
  <aside class="agent-sidebar">
    <div class="sidebar-head">
      <span class="sidebar-title">会话</span>
      <button type="button" class="sidebar-close" aria-label="关闭会话列表" @click="$emit('close')">×</button>
    </div>

    <button type="button" class="new-chat-button" @click="$emit('new')">
      <span aria-hidden="true">＋</span>
      新对话
    </button>

    <div class="search-box">
      <input
        :value="search"
        type="search"
        placeholder="搜索标题或内容"
        @input="$emit('search', $event.target.value)"
      />
    </div>

    <div class="conversation-list">
      <div v-if="loading" class="list-state">加载中…</div>
      <div v-else-if="!conversations.length" class="list-state">暂无会话</div>
      <button
        v-for="item in conversations"
        :key="item.id"
        type="button"
        class="conversation-item"
        :class="{ active: item.id === activeId, pinned: item.is_pinned }"
        @click="$emit('select', item.id)"
      >
        <div class="conversation-top">
          <span class="conversation-title">{{ item.title || '新对话' }}</span>
          <span v-if="item.is_pinned" class="pin-mark">置顶</span>
        </div>
        <div class="conversation-preview">
          {{ item.last_message_preview || '还没有消息' }}
        </div>
        <div class="conversation-meta">
          <span>{{ timeText(item) }}</span>
          <span v-if="showOwner && item.owner_name" class="owner-name">
            {{ item.owner_name }}
          </span>
        </div>
        <div class="conversation-actions" @click.stop>
          <button type="button" @click="$emit('pin', item)">
            {{ item.is_pinned ? '取消置顶' : '置顶' }}
          </button>
          <button type="button" @click="$emit('rename', item)">重命名</button>
          <button type="button" class="danger" @click="$emit('delete', item)">删除</button>
        </div>
      </button>
    </div>

    <div class="sidebar-foot">共 {{ total }} 个会话</div>
  </aside>
</template>

<script setup>
defineProps({
  conversations: { type: Array, default: () => [] },
  activeId: { type: Number, default: null },
  loading: { type: Boolean, default: false },
  search: { type: String, default: '' },
  total: { type: Number, default: 0 },
  showOwner: { type: Boolean, default: false },
})

defineEmits(['new', 'select', 'search', 'rename', 'pin', 'delete', 'close'])

function timeText(item) {
  const raw = item.last_message_at || item.updated_at || item.created_at
  if (!raw) return ''
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return ''
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<style scoped>
.agent-sidebar {
  display: flex;
  flex-direction: column;
  width: 252px;
  min-width: 252px;
  height: 100%;
  border-right: 1px solid var(--agent-line, rgba(31, 32, 38, 0.09));
  background: color-mix(in srgb, var(--agent-bg, #f6f5f2) 90%, #fff);
}
.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 54px;
  padding: 0 14px;
  border-bottom: 1px solid var(--agent-line, rgba(31, 32, 38, 0.09));
}
.sidebar-title {
  color: var(--agent-text, #1f2026);
  font-size: 13px;
  font-weight: 700;
}
.sidebar-close {
  display: none;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--agent-muted, #6f7280);
  font-size: 18px;
  cursor: pointer;
}
.new-chat-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 36px;
  margin: 12px 12px 8px;
  border: 1px solid var(--agent-accent-line, rgba(91, 110, 225, 0.38));
  border-radius: 10px;
  background: var(--agent-panel, #fffdf9);
  color: var(--agent-accent, #5b6ee1);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.new-chat-button:hover {
  background: var(--agent-accent-soft, #eef0ff);
}
.search-box {
  padding: 0 12px 8px;
}
.search-box input {
  width: 100%;
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--agent-line, rgba(31, 32, 38, 0.09));
  border-radius: 9px;
  outline: none;
  background: var(--agent-panel, #fffdf9);
  color: var(--agent-text, #1f2026);
  font-size: 12px;
}
.search-box input:focus {
  border-color: var(--agent-accent-line, rgba(91, 110, 225, 0.38));
  box-shadow: 0 0 0 3px var(--agent-accent-soft, #eef0ff);
}
.conversation-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 2px 8px 8px;
}
.list-state {
  padding: 20px 10px;
  color: var(--agent-faint, #a3a4ad);
  font-size: 12px;
  text-align: center;
}
.conversation-item {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: 100%;
  margin-bottom: 4px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--agent-text, #1f2026);
  text-align: left;
  cursor: pointer;
  transition: background-color 0.14s ease, border-color 0.14s ease;
}
.conversation-item:hover {
  background: var(--agent-hover, #f1f0ec);
}
.conversation-item.active {
  border-color: var(--agent-accent-line, rgba(91, 110, 225, 0.38));
  background: var(--agent-panel, #fffdf9);
}
.conversation-item.pinned {
  box-shadow: inset 2px 0 0 var(--agent-accent, #5b6ee1);
}
.conversation-top {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.conversation-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
  font-weight: 650;
}
.pin-mark {
  flex: none;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--agent-accent-soft, #eef0ff);
  color: var(--agent-accent, #5b6ee1);
  font-size: 9.5px;
  line-height: 15px;
}
.conversation-preview {
  overflow: hidden;
  color: var(--agent-muted, #6f7280);
  font-size: 11.5px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conversation-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  color: var(--agent-faint, #a3a4ad);
  font-size: 10.5px;
}
.owner-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conversation-actions {
  display: none;
  gap: 8px;
  padding-top: 4px;
}
.conversation-item:hover .conversation-actions,
.conversation-item.active .conversation-actions {
  display: flex;
}
.conversation-actions button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--agent-muted, #6f7280);
  font-size: 10.5px;
  cursor: pointer;
}
.conversation-actions button:hover {
  color: var(--agent-accent, #5b6ee1);
}
.conversation-actions .danger:hover {
  color: var(--agent-err, #c25566);
}
.sidebar-foot {
  padding: 8px 12px;
  border-top: 1px solid var(--agent-line, rgba(31, 32, 38, 0.09));
  color: var(--agent-faint, #a3a4ad);
  font-size: 10.5px;
  text-align: center;
}
@media (max-width: 820px) {
  .agent-sidebar {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 20;
    width: min(86vw, 300px);
    min-width: 0;
    box-shadow: 18px 0 40px -28px rgba(31, 32, 38, 0.45);
  }
  .sidebar-close {
    display: block;
  }
  .conversation-actions {
    display: flex;
  }
}
</style>
