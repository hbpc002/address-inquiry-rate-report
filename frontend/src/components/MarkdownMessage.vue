<template>
  <div class="markdown-body">
    <div v-html="html" ref="root"></div>
    <div v-if="chart" class="chart-block">
      <Echart :options="chart" :height="chartHeight" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import Echart from './Echart.vue'
import { parseMessage, renderMarkdown } from '@/utils/markdown'

const props = defineProps({
  content: { type: String, default: '' },
  chartHeight: { type: String, default: '360px' },
})

const root = ref(null)
const parsed = computed(() => parseMessage(props.content))
const html = computed(() => renderMarkdown(parsed.value.body))
const chart = computed(() => parsed.value.chart)

function decorate() {
  if (!root.value) return
  const blocks = root.value.querySelectorAll('pre code')
  blocks.forEach((block) => {
    if (!block.dataset.hl) {
      try {
        hljs.highlightElement(block)
        block.dataset.hl = '1'
      } catch (e) { /* noop */ }
    }
    // 代码块右上角加「复制」按钮
    const pre = block.parentElement
    if (pre && !pre.querySelector('.copy-btn')) {
      const btn = document.createElement('button')
      btn.className = 'copy-btn'
      btn.textContent = '复制'
      btn.onclick = () => {
        navigator.clipboard?.writeText(block.textContent)
        btn.textContent = '已复制'
        setTimeout(() => (btn.textContent = '复制'), 1500)
      }
      pre.style.position = 'relative'
      pre.appendChild(btn)
    }
  })
}

onMounted(() => nextTick(decorate))
watch(html, () => nextTick(decorate))
</script>

<style scoped>
.markdown-body {
  line-height: 1.6;
  word-break: break-word;
}
.markdown-body :deep(pre) {
  background: #f6f8fa;
  padding: 12px 14px;
  border-radius: 6px;
  overflow: auto;
  font-size: 13px;
}
.markdown-body :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #ebeef5;
  padding: 6px 10px;
}
.copy-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 12px;
  border: 1px solid #dcdfe6;
  background: #fff;
  border-radius: 4px;
  padding: 2px 8px;
  cursor: pointer;
}
.chart-block {
  margin-top: 12px;
}
</style>
