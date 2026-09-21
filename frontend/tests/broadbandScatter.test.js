import { describe, it, expect } from 'vitest'
import {
  teamName,
  toPoint,
  buildTeamMap,
  buildScatterOptions
} from '../src/utils/broadbandScatter'

function makeEmp(emp_no, name, team, recommend, success_rate) {
  return { emp_no, name, team, recommend, completed: Math.round(recommend * success_rate), success_rate }
}

describe('broadbandScatter 散点图工具函数', () => {
  it('teamName 应回退到 未知班组', () => {
    expect(teamName({ team: '云网一组' })).toBe('云网一组')
    expect(teamName({ team: '' })).toBe('未知班组')
    expect(teamName({})).toBe('未知班组')
  })

  it('toPoint 应生成 [推荐量, 成功率*100, meta] 结构', () => {
    const point = toPoint(makeEmp('KF770001', '张三', '云网一组', 4, 0.75))
    expect(point[0]).toBe(4)
    expect(point[1]).toBe(75.0)
    expect(point[2]).toMatchObject({ emp_no: 'KF770001', name: '张三', team: '云网一组', recommend: 4, completed: 3 })
  })

  it('toPoint 成功率应四舍五入到 1 位小数', () => {
    const point = toPoint(makeEmp('KF770002', '李四', '云网二组', 3, 2 / 3))
    expect(point[1]).toBe(66.7)
  })

  it('buildTeamMap 应为每个班组分配递增索引', () => {
    const items = [
      makeEmp('a', '甲', '云网一组', 1, 1),
      makeEmp('b', '乙', '云网二组', 1, 1),
      makeEmp('c', '丙', '云网一组', 1, 1),
    ]
    expect(buildTeamMap(items)).toEqual({ 云网一组: 0, 云网二组: 1 })
  })

  it('buildScatterOptions: 每个班组对应一个着色系列，图例显式限定为班组', () => {
    const items = [
      makeEmp('a', '甲', '云网一组', 3, 1),
      makeEmp('b', '乙', '云网二组', 2, 0.5),
      makeEmp('c', '丙', '云网一组', 2, 0.5),
    ]
    const options = buildScatterOptions(items)
    const series = options.series
    expect(series.map(s => s.name)).toEqual(['云网一组', '云网二组'])
    expect(series[0].data).toHaveLength(2)
    expect(series[1].data).toHaveLength(1)
    expect(series[0].itemStyle.color).not.toBe(series[1].itemStyle.color)
    expect(options.legend.data).toEqual(['云网一组', '云网二组'])
  })

  it('buildScatterOptions: 所有点都显示姓名标签（人数多也不例外）', () => {
    const items = []
    for (let i = 1; i <= 30; i++) {
      items.push(makeEmp(`e${i}`, `员工${i}`, i % 2 === 0 ? '云网一组' : '云网二组', i, 0.5))
    }
    const options = buildScatterOptions(items)
    const series = options.series
    const totalPoints = series.reduce((sum, s) => sum + s.data.length, 0)
    expect(totalPoints).toBe(items.length)
    for (const s of series) {
      expect(s.label.show).toBe(true)
      expect(s.labelLayout.hideOverlap).toBe(true)
      expect(s.labelLayout.moveOverlap).toBe('shiftY')
    }
  })

  it('buildScatterOptions: 标签样式优化（加粗、≥12号、与点同色、白色描边）', () => {
    const items = [
      makeEmp('a', '甲', '云网一组', 3, 1),
      makeEmp('b', '乙', '云网二组', 2, 0.5),
    ]
    const options = buildScatterOptions(items)
    for (const s of options.series) {
      expect(s.label.fontSize).toBeGreaterThanOrEqual(12)
      expect(s.label.fontWeight).toBe(600)
      expect(s.label.color).toBe(s.itemStyle.color)
      expect(s.label.textBorderWidth).toBe(2)
      expect(typeof s.label.formatter).toBe('function')
    }
    const name = options.series[0].label.formatter({ data: [3, 100, { name: '甲', emp_no: 'a', team: '云网一组', recommend: 3, completed: 3 }] })
    expect(name).toBe('甲')
  })

  it('buildScatterOptions: 一直启用缩放，include X/Y 双轴与双滑块', () => {
    const items = [makeEmp('a', '甲', '云网一组', 3, 1)]
    const options = buildScatterOptions(items)
    expect(options.dataZoom).toBeDefined()

    const inside = options.dataZoom.find(d => d.type === 'inside')
    expect(inside.xAxisIndex).toBe(0)
    expect(inside.yAxisIndex).toBe(0)
    expect(inside.zoomOnMouseWheel).toBe(true)
    expect(inside.moveOnMouseWheel).toBe(false)
    expect(inside.moveOnMouseMove).toBe(true)

    const xSlider = options.dataZoom.find(d => d.type === 'slider' && d.xAxisIndex === 0)
    expect(xSlider).toBeDefined()
    expect(xSlider.height).toBe(16)

    const ySlider = options.dataZoom.find(d => d.type === 'slider' && d.yAxisIndex === 0)
    expect(ySlider).toBeDefined()
    expect(ySlider.orient).toBe('vertical')
    expect(ySlider.width).toBe(14)

    expect(options.grid.bottom).toBe(90)
    expect(options.grid.right).toBe(70)
    expect(options.grid.left).toBe(45)
    expect(options.title.text).toContain('可滚轮缩放')
    expect(options.title.text).toContain('以鼠标为中心')
  })

  it('buildScatterOptions: tooltip formatter 可从散点 meta 提取员工信息', () => {
    const options = buildScatterOptions([makeEmp('a', '甲', '云网一组', 4, 0.75)])
    const tooltipText = options.tooltip.formatter({ data: [4, 75.0, { name: '甲', emp_no: 'a', team: '云网一组', recommend: 4, completed: 3 }] })
    expect(tooltipText).toContain('甲 (a)')
    expect(tooltipText).toContain('推荐量: 4')
    expect(tooltipText).toContain('成功率: 75.0%')
    expect(tooltipText).toContain('成功推荐: 3')
  })
})