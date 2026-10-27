<template>
  <span class="agent-avatar" :style="boxStyle" aria-hidden="true">
    <img
      v-if="type === 'url' && value"
      class="avatar-image"
      :src="value"
      :style="imageStyle"
      alt=""
      draggable="false"
    />
    <span
      v-else-if="type === 'svg' && value"
      class="avatar-svg"
      :style="svgStyle"
      v-html="value"
    ></span>
    <span v-else class="avatar-emoji" :style="emojiStyle">{{ value || '🤖' }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: { type: String, default: 'emoji' },
  value: { type: String, default: '🤖' },
  color: { type: String, default: '#5b6ee1' },
  offsetX: { type: Number, default: 0 },
  offsetY: { type: Number, default: 0 },
  scale: { type: Number, default: 100 },
  size: { type: Number, default: 34 },
})

const boxStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  borderColor: `color-mix(in srgb, ${props.color} 42%, transparent)`,
  background: `color-mix(in srgb, ${props.color} 13%, #fffdf9)`,
}))

const imageStyle = computed(() => ({
  transform: `translate(calc(-50% + ${props.offsetX}px), calc(-50% + ${props.offsetY}px)) scale(${props.scale / 100})`,
}))

const emojiStyle = computed(() => ({
  fontSize: `${Math.max(12, Math.round(props.size * 0.5))}px`,
}))

const svgStyle = computed(() => ({
  width: `${Math.round(props.size * 0.58)}px`,
  height: `${Math.round(props.size * 0.58)}px`,
  transform: `translate(${props.offsetX}px, ${props.offsetY}px) scale(${props.scale / 100})`,
}))
</script>

<style scoped>
.agent-avatar {
  position: relative;
  display: inline-grid;
  place-items: center;
  flex: none;
  overflow: hidden;
  border: 1px solid;
  border-radius: 50%;
  color: var(--agent-accent, #5b6ee1);
  line-height: 1;
}
.avatar-image {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  pointer-events: none;
  -webkit-user-drag: none;
}
.avatar-svg {
  display: grid;
  place-items: center;
  color: currentColor;
}
.avatar-svg :deep(svg) {
  width: 100%;
  height: 100%;
  fill: currentColor;
}
.avatar-emoji {
  display: block;
  line-height: 1;
  transform: translateY(-1px);
}
</style>
