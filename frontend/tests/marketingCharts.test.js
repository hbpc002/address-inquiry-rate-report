import { describe, it, expect } from 'vitest'
import {
  buildBusinessPieData,
  buildValidPieData,
  buildLhPieData,
  metricValue,
  rankingItems,
  buildParetoData,
  buildCrossData,
  buildTeamRankingOptions,
  buildEmployeeRankingOptions,
  buildDailyTrendOptions,
  buildDailyBusinessOptions,
  buildTeamScatterOptions,
  buildTeamRadarOptions,
  buildValidCrossOptions,
  filterMatchedTeams
} from '../src/utils/marketingCharts'

const stats = {
  total: 100,
  order_count: 60,
  inbound: 70,
  outbound: 20,
  overlay: 70,
  package_change: 20,
  overlay_day: 10,
  overlay_month: 30,
  overlay_long: 20,
  overlay_undefined: 10,
  people_count: 5
}

const teams = [
  {
    team: '热线一组',
    leader: '张三',
    people: 2,
    total: 20,
    order_count: 10,
    inbound: 15,
    outbound: 5,
    overlay: 12,
    package_change: 5,
    overlay_day: 2,
    overlay_month: 5,
    overlay_long: 3,
    overlay_undefined: 2
  },
  {
    team: '热线二组',
    leader: '李四',
    people: 3,
    total: 30,
    order_count: 24,
    inbound: 20,
    outbound: 8,
    overlay: 21,
    package_change: 6,
    overlay_day: 4,
    overlay_month: 8,
    overlay_long: 5,
    overlay_undefined: 4
  }
]

const employees = [
  {
    kf_id: 'KF001',
    name: '王五',
    team: '热线一组',
    dept: '客服部',
    group_name: '线上直办-热线',
    total: 20,
    order_count: 10,
    inbound: 15,
    outbound: 5,
    overlay: 12,
    package_change: 5,
    overlay_day: 2,
    overlay_month: 5,
    overlay_long: 3,
    overlay_undefined: 2
  },
  {
    kf_id: 'KF002',
    name: '赵六',
    team: '热线二组',
    dept: '客服部',
    group_name: '线上直办-热线',
    total: 30,
    order_count: 24,
    inbound: 20,
    outbound: 8,
    overlay: 21,
    package_change: 6,
    overlay_day: 4,
    overlay_month: 8,
    overlay_long: 5,
    overlay_undefined: 4
  }
]

const days = [
  {
    date: '2026-10-01',
    total: 20,
    order_count: 12,
    inbound: 15,
    outbound: 5,
    overlay: 14,
    package_change: 4,
    overlay_day: 2,
    overlay_month: 6,
    overlay_long: 4,
    overlay_undefined: 2
  },
  {
    date: '2026-10-02',
    total: 30,
    order_count: 18,
    inbound: 20,
    outbound: 8,
    overlay: 21,
    package_change: 7,
    overlay_day: 3,
    overlay_month: 8,
    overlay_long: 6,
    overlay_undefined: 4
  }
]

describe('营销统计图表数据构建', () => {
  it('存在正常班组时过滤未匹配班组，全部未匹配时保留兜底', () => {
    const unmatched = {
      team: '未匹配班组',
      leader: '',
      people: 1,
      total: 10,
      order_count: 5,
      inbound: 8,
      outbound: 2,
      overlay: 7,
      package_change: 2,
      overlay_day: 1,
      overlay_month: 3,
      overlay_long: 2,
      overlay_undefined: 1
    }

    expect(filterMatchedTeams([...teams, unmatched]).map(item => item.displayName)).toEqual([
      '热线一组', '热线二组'
    ])
    expect(filterMatchedTeams([unmatched]).map(item => item.displayName)).toEqual(['未匹配班组'])
  })

  it('业务构成、有效期、来话去话饼图数据应包含其他和未标注分类', () => {
    expect(buildBusinessPieData(stats)).toEqual([
      { name: '叠加包', value: 70 },
      { name: '套餐变更', value: 20 },
      { name: '其他', value: 10 }
    ])
    expect(buildValidPieData(stats)).toEqual([
      { name: '日包', value: 10 },
      { name: '月包', value: 30 },
      { name: '长期包', value: 20 },
      { name: '未定义', value: 10 }
    ])
    expect(buildLhPieData(stats)).toEqual([
      { name: '来话', value: 70 },
      { name: '去话', value: 20 },
      { name: '未标注', value: 10 }
    ])
  })

  it('应正确计算人数、人均办理量、人均订单数和订单覆盖率', () => {
    const team = teams[0]
    expect(metricValue(team, 'people')).toBe(2)
    expect(metricValue(team, 'avg_total')).toBe(10)
    expect(metricValue(team, 'avg_order')).toBe(5)
    expect(metricValue(team, 'order_rate')).toBe(50)
  })

  it('排行数据应按指标倒序并截取 Top N，横向图表数据反转为从下到上递增', () => {
    const ranked = rankingItems(teams, { metric: 'total', limit: 1 })
    expect(ranked).toHaveLength(1)
    expect(ranked[0].team).toBe('热线二组')

    const options = buildTeamRankingOptions(teams, { metric: 'total', limit: 10 })
    expect(options.yAxis.data).toEqual(['热线一组', '热线二组'])
    expect(options.series[0].data[0].value).toBe(20)
    expect(options.series[0].data[1].value).toBe(30)
    expect(options.series[0].data[1].team).toBe('热线二组')
    const tooltip = options.tooltip.formatter([{ data: options.series[0].data[1] }])
    expect(tooltip).toContain('热线二组')
    expect(tooltip).toContain('组长：李四')
    expect(tooltip).toContain('人数：3')
  })

  it('员工排行数据应携带工号供图表点击筛选', () => {
    const options = buildEmployeeRankingOptions(employees, { metric: 'order_count', limit: 10 })
    const target = options.series[0].data.find(item => item.kf_id === 'KF002')
    expect(target).toBeTruthy()
    expect(target.value).toBe(24)
    expect(target.name).toBe('赵六')
  })

  it('帕累托数据应计算累计占比', () => {
    const pareto = buildParetoData(teams, { metric: 'total', limit: 10 })
    expect(pareto.labels).toEqual(['热线二组', '热线一组'])
    expect(pareto.values).toEqual([30, 20])
    expect(pareto.cumulative).toEqual([60, 100])
  })

  it('交叉分析应生成业务、来话去话、有效期结构', () => {
    const business = buildCrossData(teams, { kind: 'business', limit: 10 })
    expect(business.categories).toEqual(['热线二组', '热线一组'])
    expect(business.series.map(item => item.name)).toEqual(['叠加包', '套餐变更', '其他'])
    expect(business.series[0].data).toEqual([21, 12])
    expect(business.series[2].data).toEqual([3, 3])

    const lh = buildCrossData(teams, { kind: 'lh', limit: 10 })
    expect(lh.series.map(item => item.name)).toEqual(['来话', '去话', '未标注'])
    expect(lh.series[2].data).toEqual([2, 0])

    const validOptions = buildValidCrossOptions(teams, { title: '班组有效期', limit: 10 })
    expect(validOptions.series.map(item => item.name)).toEqual(['日包', '月包', '长期包', '未定义'])
  })

  it('每日趋势与每日业务结构应覆盖核心指标', () => {
    const trend = buildDailyTrendOptions(days)
    expect(trend.xAxis.data).toEqual(['2026-10-01', '2026-10-02'])
    expect(trend.series.map(item => item.name)).toEqual([
      '产品办理量', '订单数', '来话', '去话', '叠加包', '套餐变更'
    ])
    expect(trend.series[0].data).toEqual([20, 30])

    const business = buildDailyBusinessOptions(days)
    expect(business.series.map(item => item.name)).toEqual(['叠加包', '套餐变更', '其他'])
    expect(business.series[2].data).toEqual([2, 2])
  })

  it('班组散点图应使用人均办理量、订单覆盖率和人数三个维度', () => {
    const options = buildTeamScatterOptions(teams)
    const target = options.series[0].data.find(item => item.team === '热线二组')
    expect(target.value).toEqual([10, 80, 3])
    expect(options.xAxis.name).toBe('人均办理量')
    expect(options.yAxis.name).toBe('订单覆盖率(%)')
  })

  it('班组雷达图应包含六个对比指标', () => {
    const options = buildTeamRadarOptions(teams)
    expect(options.radar.indicator.map(item => item.name)).toEqual([
      '办理量', '订单数', '来话', '去话', '叠加包', '套餐变更'
    ])
    expect(options.series[0].data).toHaveLength(2)
  })
})
