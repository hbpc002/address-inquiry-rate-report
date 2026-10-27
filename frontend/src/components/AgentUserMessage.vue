<template>
  <article class="agent-user">
    <div class="user-card">
      <div class="user-head">
        <span class="user-avatar">你</span>
        <span class="user-author">你</span>
        <time v-if="timeText" class="user-time">{{ timeText }}</time>
      </div>
      <div class="user-text">{{ message.content }}</div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: { type: Object, required: true },
})

const timeText = computed(() => {
  if (!props.message.createdAt) return ''
  const d = new Date(props.message.createdAt)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})
</script>

<style scoped>
.agent-user {
  display: flex;
  justify-content: flex-end;
}
.user-card {
  width: min(100%, 720px);
  padding: 12px 16px 14px;
  border: 1px solid var(--agent-line, rgba(31, 32, 38, 0.09));
  border-radius: var(--agent-radius, 12px);
  background: var(--agent-user-card, #fffdf9);
  color: var(--agent-text, #1f2026);
  box-shadow: 0 1px 2px rgba(31, 32, 38, 0.03);
}
.user-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  margin-bottom: 5px;
  font-size: 12.5px;
  line-height: 22px;
}
.user-avatar {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--agent-accent-soft, #eef0ff);
  color: var(--agent-accent, #5b6ee1);
  font-size: 10px;
  font-weight: 700;
  flex: none;
}
.user-author {
  font-weight: 650;
  color: var(--agent-text, #1f2026);
}
.user-time {
  color: var(--agent-faint, #a3a4ad);
  font-variant-numeric: tabular-nums;
}
.user-text {
  padding-left: 30px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  text-wrap: pretty;
  line-height: 1.65;
  font-size: 14.5px;
}
</style>
