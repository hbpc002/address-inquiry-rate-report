import { describe, it, expect } from 'vitest'
import {
  SHOW_ALL_LABEL_THRESHOLD,
  TOP_LABEL_COUNT,
  ZOOM_THRESHOLD,
  teamName,
  toPoint,
  buildTeamMap,
  selectLabeledItems,
  buildScatterOptions
} from '../src/utils/broadbandScatter'

function makeEmp(emp_no, name, team, recommend, success_rate) {
  return { emp_no, name, team, recommend, completed: Math.round(recommend * success_rate), success_rate }
}

describe('broadbandScatter 散点图工具函数', () => {
  it('应导出配置阈值常量', () => {
    expect(SHOW_ALL_LABEL_THRESHOLD).toBe(20)
    expect(TOP_LABEL_COUNT).toBe(12)
    expect(ZOOM_THRESHOLD).toBe(60)
  })

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

  it('selectLabeledItems: 人数不超过阈值时全量返回(不改顺序)', () => {
    const items = [
      makeEmp('a', '甲', '云网一组', 1, 1),
      makeEmp('b', '乙', '云网二组', 2, 0.5),
    ]
    expect(selectLabeledItems(items)).toBe(items)
  })

  it('selectLabeledItems: 人数超阈值只取推荐量 TopN，同推荐量按成功率降序', () => {
    const items = []
    for (let i = 1; i <= 30; i++) {
      items.push(makeEmp(`e${i}`, `员工${i}`, '云网一组', i, i / 30))
    }
    const labeled = selectLabeledItems(items)
    expect(labeled).toHaveLength(TOP_LABEL_COUNT)
    expect(labeled[0].emp_no).toBe('e30')
    expect(labeled[TOP_LABEL_COUNT - 1].emp_no).toBe('e19')
  })

  it('selectLabeledItems: 同推荐量时按成功率降序、再按姓名升序', () => {
    const items = [
      makeEmp('a', 'a1', '云网一组', 10, 0.3),
      makeEmp('b', 'b1', '云网一组', 10, 0.8),
      makeEmp('c', 'c1', '云网一组', 10, 0.8),
    ]
    const items2 = selectLabeledItems([...items, ...Array(20).fill(0).map((_, i) => makeEmp(`x${i}`, `x${i}`, '云网二组', 1, 0.1))])
    const topThree = items2.slice(0, 3).map(i => i.name)
    expect(topThree).toEqual(['b1', 'c1', 'a1'])
  })

  it('buildScatterOptions: 每个班组对应一个着色系列，另含隐形标签层', () => {
    const items = [
      makeEmp('a', '甲', '云网一组', 3, 1),
      makeEmp('b', '乙', '云网二组', 2, 0.5),
      makeEmp('c', '丙', '云网一组', 2, 0.5),
    ]
    const options = buildScatterOptions(items)
    const teamSeries = options.series.filter(s => s.name)
    expect(teamSeries.map(s => s.name)).toEqual(['云网一组', '云网二组'])
    expect(teamSeries[0].data).toHaveLength(2)
    expect(teamSeries[1].data).toHaveLength(1)
    expect(teamSeries[0].itemStyle.color).not.toBe(teamSeries[1].itemStyle.color)
    expect(options.series).toHaveLength(2 + 1)

    const labelSeries = options.series.find(s => s.name === '')
    expect(labelSeries.symbolSize).toBe(0)
    expect(labelSeries.silent).toBe(true)
    expect(labelSeries.label.show).toBe(true)
    expect(labelSeries.labelLayout).toEqual({ hideOverlap: true })
    // 人数少于阈值时全部标姓名
    expect(labelSeries.data).toHaveLength(3)
  })

  it('buildScatterOptions: 数据点 color 数量与 legend 一致，图例显式限定为班组', () => {
    const items = [
      makeEmp('a', '甲', '云网一组', 3, 1),
      makeEmp('b', '乙', '云网二组', 2, 0.5),
    ]
    const options = buildScatterOptions(items)
    expect(options.legend.data).toEqual(['云网一组', '云网二组'])
  })

  it('buildScatterOptions: 人数超阈值时标签层只含 TopN', () => {
    const items = []
    for (let i = 1; i <= 30; i++) {
      items.push(makeEmp(`e${i}`, `员工${i}`, '云网一组', i, i / 30))
    }
    const options = buildScatterOptions(items)
    const labelSeries = options.series.find(s => s.name === '')
    expect(labelSeries.data).toHaveLength(TOP_LABEL_COUNT)
    expect(labelSeries.data[0][2].emp_no).toBe('e30')
  })

  it('buildScatterOptions: 人数超60自动启用缩放并抬高 grid.bottom', () => {
    const items = []
    for (let i = 1; i <= 70; i++) {
      items.push(makeEmp(`e${i}`, `员工${i}`, '云网一组', 1, 0.5))
    }
    const options = buildScatterOptions(items)
    expect(options.dataZoom).toBeDefined()
    const types = options.dataZoom.map(d => d.type)
    expect(types).toContain('inside')
    expect(types).toContain('slider')
    expect(options.grid.bottom).toBe(90)
    expect(options.title.text).toContain('可滚轮缩放')
  })

  it('buildScatterOptions: 人数不超过60时不启用缩放', () => {
    const items = [makeEmp('a', '甲', '云网一组', 3, 1)]
    const options = buildScatterOptions(items)
    expect(options.dataZoom).toBeUndefined()
    expect(options.grid.bottom).toBe('12%')
    expect(options.title.text).not.toContain('可滚轮缩放')
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