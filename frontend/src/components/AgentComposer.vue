<template>
  <footer class="agent-composer">
    <div class="composer-card">
      <textarea
        ref="textareaRef"
        class="composer-input"
        :value="modelValue"
        rows="1"
        placeholder="输入问题，Enter 发送 / Shift+Enter 换行"
        @input="onInput"
        @keydown="onKeydown"
      ></textarea>

      <div class="composer-row">
        <div class="composer-tools">
          <el-select
            v-if="providers.length"
            :model-value="provider"
            size="small"
            placeholder="提供商"
            class="model-select provider-select"
            @update:model-value="$emit('update:provider', $event)"
          >
            <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.name" />
          </el-select>
          <el-select
            v-if="models.length"
            :model-value="model"
            size="small"
            placeholder="模型"
            class="model-select"
            @update:model-value="$emit('update:model', $event)"
          >
            <el-option v-for="m in models" :key="m" :label="m" :value="m" />
          </el-select>
        </div>

        <div class="composer-actions">
          <span class="composer-hint">Enter 发送</span>
          <button
            v-if="streaming"
            type="button"
            class="round-button stop-button"
            title="停止生成"
            aria-label="停止生成"
            @click="$emit('stop')"
          >
            <span class="stop-square"></span>
          </button>
          <button
            v-else
            type="button"
            class="round-button send-button"
            :class="{ ready: canSend }"
            :disabled="!canSend"
            title="发送"
            aria-label="发送"
            @click="onSend"
          >
            <span class="send-arrow">↑</span>
          </button>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  streaming: { type: Boolean, default: false },
  providers: { type: Array, default: () => [] },
  models: { type: Array, default: () => [] },
  provider: { type: String, default: '' },
  model: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'update:provider', 'update:model', 'send', 'stop'])
const textareaRef = ref(null)
const canSend = computed(() => !!props.modelValue.trim() && !props.streaming)

function resize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 220)}px`
}

function onInput(event) {
  emit('update:modelValue', event.target.value)
  nextTick(resize)
}

function onKeydown(event) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  onSend()
}

function onSend() {
  if (!canSend.value) return
  emit('send')
  nextTick(resize)
}

watch(
  () => props.modelValue,
  () => nextTick(resize)
)
</script>

<style scoped>
.agent-composer {
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
  padding: 4px 20px calc(env(safe-area-inset-bottom) + 14px);
}
.composer-card {
  border: 1px solid var(--agent-line, rgba(31, 32, 38, 0.1));
  border-radius: var(--agent-radius-lg, 14px);
  background: var(--agent-panel, #fffdf9);
  box-shadow: 0 14px 34px -24px rgba(31, 32, 38, 0.35), 0 1px 2px rgba(31, 32, 38, 0.04);
  overflow: hidden;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}
.composer-card:focus-within {
  border-color: var(--agent-accent-line, rgba(91, 110, 225, 0.38));
  box-shadow: 0 14px 34px -24px rgba(31, 32, 38, 0.35), 0 0 0 3px var(--agent-accent-soft, #eef0ff);
}
.composer-input {
  display: block;
  width: 100%;
  min-height: 48px;
  max-height: 220px;
  padding: 14px 16px 2px;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--agent-text, #1f2026);
  font: inherit;
  font-size: 15px;
  line-height: 1.55;
  resize: none;
  overflow-y: auto;
}
.composer-input::placeholder {
  color: var(--agent-faint, #a3a4ad);
}
.composer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 10px 8px;
}
.composer-tools {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}
.model-select {
  width: 128px;
}
.provider-select {
  width: 116px;
}
.composer-actions {
  display: flex;
  align-items: center;
  gap: 9px;
  flex: none;
}
.composer-hint {
  color: var(--agent-faint, #a3a4ad);
  font-size: 11.5px;
  white-space: nowrap;
}
.round-button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 50%;
  flex: none;
  cursor: pointer;
  transition: background-color 0.14s ease, color 0.14s ease, transform 90ms ease;
}
.round-button:active {
  transform: scale(0.92);
}
.send-button {
  background: var(--agent-raised, #f0efeb);
  color: var(--agent-faint, #a3a4ad);
  cursor: default;
}
.send-button.ready {
  background: var(--agent-accent, #5b6ee1);
  color: #fff;
  cursor: pointer;
}
.send-button.ready:hover {
  background: var(--agent-accent-strong, #485bd6);
}
.send-arrow {
  margin-top: -1px;
  font-size: 19px;
  font-weight: 650;
  line-height: 1;
}
.stop-button {
  background: var(--agent-err-soft, #fdeef1);
}
.stop-button:hover {
  background: #f9dde3;
}
.stop-square {
  width: 11px;
  height: 11px;
  border-radius: 2px;
  background: var(--agent-err, #c25566);
}
:deep(.el-select__wrapper) {
  box-shadow: none !important;
  background: var(--agent-raised, #f0efeb) !important;
  border-radius: 999px;
  min-height: 28px;
}
:deep(.el-select__placeholder),
:deep(.el-select__selected-item) {
  font-size: 12px;
}
@media (max-width: 699px) {
  .agent-composer {
    padding-inline: 12px;
    padding-bottom: calc(env(safe-area-inset-bottom) + 8px);
  }
  .composer-input {
    font-size: 16px;
  }
  .provider-select {
    display: none;
  }
  .model-select {
    width: 112px;
  }
  .composer-hint {
    display: none;
  }
}
</style>
