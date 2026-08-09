import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'
import {
  createPieOptions,
  createBarOptions,
  createLineOptions,
  createHorizontalBarOptions,
  createMultiBarOptions,
  CHART_COLORS
} from '../src/utils/echarts'

describe('echarts 图表工具函数', () => {
  it('应导出全部图表构造函数', () => {
    expect(typeof createPieOptions).toBe('function')
    expect(typeof createBarOptions).toBe('function')
    expect(typeof createLineOptions).toBe('function')
    expect(typeof createHorizontalBarOptions).toBe('function')
    expect(typeof createMultiBarOptions).toBe('function')
    expect(Array.isArray(CHART_COLORS)).toBe(true)
  })

  it('createMultiBarOptions 应生成多系列柱状图配置（支持班组晚签/早退、分时分布、班次结构图）', () => {
    const options = createMultiBarOptions(['班组A', '班组B'], [
      { name: '晚签人数', data: [2, 0] },
      { name: '早退人数', data: [1, 3] }
    ], '班组晚签/早退人数')
    expect(options.title.text).toBe('班组晚签/早退人数')
    expect(options.xAxis.data).toEqual(['班组A', '班组B'])
    expect(options.series).toHaveLength(2)
    expect(options.series[0].name).toBe('晚签人数')
    expect(options.series[0].data).toEqual([2, 0])
    expect(options.series[0].type).toBe('bar')
    // 每个系列应有独立配色，避免同色柱不可区分
    expect(options.series[0].itemStyle.color).not.toBe(options.series[1].itemStyle.color)
  })

  it('CheckinReport.vue 应导入所有用到的 echarts 工具函数（防止 create* 漏导导致图表空白）', () => {
    const source = fs.readFileSync(path.resolve(__dirname, '../src/views/CheckinReport.vue'), 'utf-8')
    const importLine = source.match(/import\s*\{([^}]*)\}\s*from\s*['"]\.\.\/utils\/echarts['"]/)?.[1] || ''
    const used = new Set()
    for (const m of source.matchAll(/\b(create[A-Z]\w*|CHART_COLORS)\b/g)) {
      used.add(m[1])
    }
    for (const id of used) {
      expect(importLine, `未在 import 中找到 ${id}`).toContain(id)
    }
  })
})