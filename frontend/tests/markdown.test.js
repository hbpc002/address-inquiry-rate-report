import { describe, it, expect } from 'vitest'
import { parseMessage, renderMarkdown } from '@/utils/markdown'

describe('parseMessage', () => {
  it('提取 chart-json 并清理正文', () => {
    const raw = '这是结论。\n```chart-json\n{"title":{"text":"x"},"series":[{"type":"bar","data":[1]}]}\n```'
    const { body, chart } = parseMessage(raw)
    expect(chart).not.toBeNull()
    expect(chart.title.text).toBe('x')
    expect(body).not.toContain('chart-json')
  })

  it('无图表时 chart 为 null', () => {
    const { body, chart } = parseMessage('纯文本结论')
    expect(chart).toBeNull()
    expect(body).toBe('纯文本结论')
  })

  it('非法 JSON 图表不崩溃', () => {
    const raw = '结论\n```chart-json\n{not json\n```'
    const { chart, body } = parseMessage(raw)
    expect(chart).toBeNull()
    expect(body).toContain('结论')
  })
})

describe('renderMarkdown', () => {
  it('返回 HTML 字符串', () => {
    const html = renderMarkdown('**加粗**')
    expect(html).toContain('<strong>')
  })
})
