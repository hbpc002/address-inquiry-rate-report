import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const CHART_RE = /```chart-json\s*([\s\S]*?)```/i

/**
 * 将智能体返回的文本拆为「正文 Markdown」与可选的「ECharts 配置」。
 * chart-json 代码块会被提取出来用于图表渲染，不出现在正文中。
 */
export function parseMessage(raw) {
  const text = raw || ''
  const m = text.match(CHART_RE)
  let chart = null
  let body = text
  if (m) {
    try {
      chart = JSON.parse(m[1].trim())
    } catch (e) {
      chart = null
    }
    body = text.replace(CHART_RE, '').trim()
  }
  return { body, chart }
}

export function renderMarkdown(md) {
  return marked.parse(md || '')
}

export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}
