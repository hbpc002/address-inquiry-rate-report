import { describe, it, expect } from 'vitest'
import {
  teamName,
  axisValue,
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

  it('buildScatterOptions: 一直启用缩放，X/Y 各一个 inside 实例以支持双向拖动', () => {
    const items = [makeEmp('a', '甲', '云网一组', 3, 1)]
    const options = buildScatterOptions(items)
    expect(options.dataZoom).toBeDefined()

    const insideList = options.dataZoom.filter(d => d.type === 'inside')
    expect(insideList).toHaveLength(2)

    const xInside = insideList.find(d => d.xAxisIndex === 0)
    expect(xInside).toBeDefined()
    expect(xInside.yAxisIndex).toBeUndefined()

    const yInside = insideList.find(d => d.yAxisIndex === 0)
    expect(yInside).toBeDefined()
    expect(yInside.xAxisIndex).toBeUndefined()

    for (const inside of insideList) {
      expect(inside.zoomOnMouseWheel).toBe(true)
      expect(inside.moveOnMouseWheel).toBe(false)
      expect(inside.moveOnMouseMove).toBe(true)
    }

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
    expect(options.title.show).toBe(true)
    expect(options.title.text).toContain('可滚轮缩放')
    expect(options.title.text).toContain('以鼠标为中心')
  })

  it('buildScatterOptions: 展开时可以隐藏散点图自带标题', () => {
    const items = [makeEmp('a', '甲', '云网一组', 3, 1)]
    expect(buildScatterOptions(items).title.show).toBe(true)
    expect(buildScatterOptions(items, { showTitle: false }).title.show).toBe(false)
  })

  it('buildScatterOptions: tooltip formatter 可从散点 meta 提取员工信息', () => {
    const options = buildScatterOptions([makeEmp('a', '甲', '云网一组', 4, 0.75)])
    const tooltipText = options.tooltip.formatter({ data: [4, 75.0, { name: '甲', emp_no: 'a', team: '云网一组', recommend: 4, completed: 3 }] })
    expect(tooltipText).toContain('甲 (a)')
    expect(tooltipText).toContain('推荐量: 4')
    expect(tooltipText).toContain('成功率(%): 75%')
    expect(tooltipText).toContain('成功推荐: 3')
  })

  describe('自定义轴（推荐量/成功推荐/成功率）', () => {
    it('axisValue 按字段取整与百分比换算', () => {
      const item = makeEmp('a', '甲', '云网一组', 4, 0.75)
      expect(axisValue(item, 'recommend')).toBe(4)
      expect(axisValue(item, 'completed')).toBe(3)
      expect(axisValue(item, 'success_rate')).toBe(75.0)
      expect(axisValue(item, 'unknown')).toBe(4)
    })

    it('toPoint 支持自定义 X/Y 字段', () => {
      const item = makeEmp('a', '甲', '云网一组', 4, 0.75)
      const point = toPoint(item, 'completed', 'recommend')
      expect(point[0]).toBe(3)
      expect(point[1]).toBe(4)
      expect(point[2]).toMatchObject({ name: '甲', completed: 3 })
    })

    it('buildScatterOptions 自定义轴名与数据坐标', () => {
      const options = buildScatterOptions(
        [makeEmp('a', '甲', '云网一组', 5, 0.6), makeEmp('b', '乙', '云网一组', 2, 0.5)],
        { xField: 'completed', yField: 'recommend' }
      )
      expect(options.xAxis.name).toBe('成功推荐')
      expect(options.yAxis.name).toBe('推荐量')
      expect(options.xAxis.min).toBe(0)
      expect(options.xAxis.max).toBeUndefined()
      expect(options.yAxis.max).toBeUndefined()
      const pts = options.series[0].data
      expect(pts[0][0]).toBe(3)
      expect(pts[0][1]).toBe(5)
      expect(pts[1][0]).toBe(1)
      expect(pts[1][1]).toBe(2)
    })

    it('成功率作为 Y 轴时保留 0-100 区间与 % 后缀', () => {
      const options = buildScatterOptions([makeEmp('a', '甲', '云网一组', 4, 0.5)])
      expect(options.yAxis.name).toBe('成功率(%)')
      expect(options.yAxis.min).toBe(0)
      expect(options.yAxis.max).toBe(100)
      const text = options.tooltip.formatter({ data: [4, 50, { name: '甲', completed: 2 }] })
      expect(text).toContain('成功率(%): 50%')
    })

    it('默认参数保持推荐量×成功率输出不变', () => {
      const options = buildScatterOptions([makeEmp('a', '甲', '云网一组', 4, 0.25)])
      expect(options.xAxis.name).toBe('推荐量')
      expect(options.yAxis.name).toBe('成功率(%)')
      expect(options.series[0].data[0]).toEqual([4, 25.0, {
        emp_no: 'a', name: '甲', team: '云网一组', recommend: 4, completed: 1
      }])
    })
  })
})