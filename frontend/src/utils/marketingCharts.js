import {
  CHART_COLORS,
  createBarOptions,
  createPieOptions,
  createHorizontalBarOptions,
  createStackedBarOptions,
  createMultiLineOptions
} from './echarts'

export const RANKING_METRICS = [
  { key: 'total', label: '产品办理量', unit: '单' },
  { key: 'order_count', label: '订单数', unit: '单' },
  { key: 'inbound', label: '来话办理量', unit: '单' },
  { key: 'outbound', label: '去话办理量', unit: '单' },
  { key: 'overlay', label: '叠加包', unit: '单' },
  { key: 'package_change', label: '套餐变更', unit: '单' },
  { key: 'overlay_day', label: '日包', unit: '单' },
  { key: 'overlay_month', label: '月包', unit: '单' },
  { key: 'overlay_long', label: '长期包', unit: '单' },
  { key: 'overlay_undefined', label: '未定义', unit: '单' },
  { key: 'people', label: '人数', unit: '人' },
  { key: 'avg_total', label: '人均办理量', unit: '单/人' },
  { key: 'avg_order', label: '人均订单数', unit: '单/人' },
  { key: 'order_rate', label: '订单覆盖率', unit: '%' }
]

export const TOP_LIMITS = [10, 20, 50]

export const UNASSIGNED_TEAM = '未匹配班组'

const METRIC_MAP = Object.fromEntries(RANKING_METRICS.map(item => [item.key, item]))

function toNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}

function round(value, digits = 2) {
  const factor = 10 ** digits
  return Math.round(toNumber(value) * factor) / factor
}

export function metricLabel(metric) {
  return METRIC_MAP[metric]?.label || metric
}

export function metricUnit(metric) {
  return METRIC_MAP[metric]?.unit || ''
}

export function metricValue(item, metric) {
  if (!item) return 0
  if (metric === 'people') return toNumber(item.people)
  if (metric === 'avg_total') {
    const people = toNumber(item.people)
    return people ? toNumber(item.total) / people : 0
  }
  if (metric === 'avg_order') {
    const people = toNumber(item.people)
    return people ? toNumber(item.order_count) / people : 0
  }
  if (metric === 'order_rate') {
    const total = toNumber(item.total)
    return total ? (toNumber(item.order_count) / total) * 100 : 0
  }
  return toNumber(item[metric])
}

export function formatMetricValue(value, metric) {
  const number = toNumber(value)
  if (metric === 'order_rate') return `${number.toFixed(2)}%`
  if (metric === 'avg_total' || metric === 'avg_order') return number.toFixed(2)
  return number.toLocaleString('zh-CN')
}

function employeeLabel(item) {
  return item.name || item.kf_id || '未匹配员工'
}

function teamLabel(item) {
  return item.team_label || item.team || UNASSIGNED_TEAM
}

function groupLabel(item) {
  return item.group_name || '未分组'
}

function productLabel(item) {
  return item.product_name || item.product_id || '未匹配产品'
}

export function enrichEmployees(employees = []) {
  return employees.map(item => ({
    ...item,
    displayName: employeeLabel(item),
    label: employeeLabel(item),
    people: 1
  }))
}

export function enrichTeams(teams = []) {
  return teams.map(item => ({
    ...item,
    displayName: teamLabel(item),
    label: teamLabel(item),
    people: toNumber(item.people)
  }))
}

export function filterMatchedTeams(teams = []) {
  const items = enrichTeams(teams)
  const matched = items.filter(item => item.team && item.team !== UNASSIGNED_TEAM)
  return matched.length ? matched : items
}

export function enrichGroups(groups = []) {
  return groups.map(item => ({
    ...item,
    displayName: groupLabel(item),
    label: groupLabel(item),
    people: toNumber(item.people)
  }))
}

export function enrichProducts(products = []) {
  return products.map(item => ({
    ...item,
    displayName: productLabel(item),
    label: productLabel(item)
  }))
}

export function buildBusinessPieData(stats = {}) {
  const total = toNumber(stats.total)
  const overlay = toNumber(stats.overlay)
  const packageChange = toNumber(stats.package_change)
  return [
    { name: '叠加包', value: overlay },
    { name: '套餐变更', value: packageChange },
    { name: '其他', value: Math.max(0, total - overlay - packageChange) }
  ].filter(item => item.value > 0)
}

export function buildValidPieData(stats = {}) {
  return [
    { name: '日包', value: toNumber(stats.overlay_day) },
    { name: '月包', value: toNumber(stats.overlay_month) },
    { name: '长期包', value: toNumber(stats.overlay_long) },
    { name: '未定义', value: toNumber(stats.overlay_undefined) }
  ].filter(item => item.value > 0)
}

export function buildLhPieData(stats = {}) {
  const total = toNumber(stats.total)
  const inbound = toNumber(stats.inbound)
  const outbound = toNumber(stats.outbound)
  return [
    { name: '来话', value: inbound },
    { name: '去话', value: outbound },
    { name: '未标注', value: Math.max(0, total - inbound - outbound) }
  ].filter(item => item.value > 0)
}

export function buildBusinessPieOptions(stats) {
  return createPieOptions(buildBusinessPieData(stats), '业务构成', CHART_COLORS, '单')
}

export function buildValidPieOptions(stats) {
  return createPieOptions(buildValidPieData(stats), '叠加包有效期构成', CHART_COLORS, '单')
}

export function buildLhPieOptions(stats) {
  return createPieOptions(buildLhPieData(stats), '来话/去话构成', CHART_COLORS, '单')
}

export function buildVolumeOrderOptions(stats = {}) {
  return createBarOptions(
    ['产品办理量', '订单数'],
    [toNumber(stats.total), toNumber(stats.order_count)],
    '办理量与订单数对比',
    '',
    '单'
  )
}

export function buildPerPersonOptions(stats = {}) {
  const people = toNumber(stats.people_count)
  return createBarOptions(
    ['人均办理量', '人均订单数'],
    [
      round(people ? toNumber(stats.total) / people : 0),
      round(people ? toNumber(stats.order_count) / people : 0)
    ],
    '人均办理效率',
    '',
    '单/人'
  )
}

export function buildOrderRateOptions(stats = {}) {
  const total = toNumber(stats.total)
  return createBarOptions(
    ['订单覆盖率'],
    [round(total ? (toNumber(stats.order_count) / total) * 100 : 0)],
    '订单覆盖率',
    '',
    '%'
  )
}

export function rankingItems(items = [], { metric = 'total', limit = 10, labelKey = 'displayName' } = {}) {
  return [...items]
    .map(item => ({
      ...item,
      _value: metricValue(item, metric),
      _label: item[labelKey] || item.displayName || item.label || item.name || item.team || item.group_name || item.product_name || item.product_id || ''
    }))
    .sort((a, b) => b._value - a._value)
    .slice(0, limit)
}

function rankingTooltip(data, metric) {
  if (!data) return ''
  const lines = [data._label || data.name || '']
  if (data.kf_id) lines.push(`工号：${data.kf_id}`)
  if (data.team) lines.push(`班组：${data.team_label || data.team}`)
  if (data.dept) lines.push(`部门：${data.dept}`)
  if (data.leader) lines.push(`组长：${data.leader}`)
  if (data.people && metric !== 'people') lines.push(`人数：${data.people}`)
  if (data.product_id && data.product_name) lines.push(`产品ID：${data.product_id}`)
  lines.push(`${metricLabel(metric)}：${formatMetricValue(data._value, metric)}`)
  if (metric !== 'total') lines.push(`产品办理量：${toNumber(data.total).toLocaleString('zh-CN')}`)
  if (metric !== 'order_count') lines.push(`订单数：${toNumber(data.order_count).toLocaleString('zh-CN')}`)
  return lines.join('\n')
}

export function buildRankingOptions(items = [], {
  metric = 'total',
  limit = 10,
  title = '',
  labelKey = 'displayName',
  tooltipFormatter = null
} = {}) {
  const ranked = rankingItems(items, { metric, limit, labelKey })
  const display = [...ranked].reverse()
  const yData = display.map(item => item._label)
  const xData = display.map(item => ({
    ...item,
    name: item._label,
    value: round(item._value)
  }))
  const formatter = tooltipFormatter
    ? params => tooltipFormatter(Array.isArray(params) ? params[0]?.data : params?.data, metric, params)
    : params => rankingTooltip(Array.isArray(params) ? params[0]?.data : params?.data, metric)

  return createHorizontalBarOptions(
    yData,
    xData,
    title || `${metricLabel(metric)}排行`,
    '',
    `${metricLabel(metric)}${metricUnit(metric) ? `（${metricUnit(metric)}）` : ''}`,
    formatter
  )
}

export function buildTeamRankingOptions(teams = [], options = {}) {
  return buildRankingOptions(enrichTeams(teams), {
    title: `班组${metricLabel(options.metric || 'total')}排行`,
    ...options
  })
}

export function buildEmployeeRankingOptions(employees = [], options = {}) {
  return buildRankingOptions(enrichEmployees(employees), {
    title: `员工${metricLabel(options.metric || 'total')}排行`,
    ...options
  })
}

export function buildProductRankingOptions(products = [], options = {}) {
  return buildRankingOptions(enrichProducts(products), {
    title: `产品${metricLabel(options.metric || 'total')}排行`,
    ...options
  })
}

export function buildGroupRankingOptions(groups = [], options = {}) {
  return buildRankingOptions(enrichGroups(groups), {
    title: `行分类${metricLabel(options.metric || 'total')}排行`,
    ...options
  })
}

export function buildParetoData(items = [], { metric = 'total', limit = 20, labelKey = 'displayName' } = {}) {
  const ranked = rankingItems(items, { metric, limit, labelKey })
  const labels = ranked.map(item => item._label)
  const values = ranked.map(item => round(item._value))
  const total = values.reduce((sum, value) => sum + value, 0)
  let running = 0
  const cumulative = values.map(value => {
    running += value
    return total ? round((running / total) * 100) : 0
  })
  return { ranked, labels, values, cumulative, total }
}

export function buildParetoOptions(items = [], {
  metric = 'total',
  limit = 20,
  title = '',
  labelKey = 'displayName'
} = {}) {
  const { labels, values, cumulative } = buildParetoData(items, { metric, limit, labelKey })
  const option = {
    title: { text: title || `${metricLabel(metric)}帕累托图`, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: [metricLabel(metric), '累计占比'], bottom: 0 },
    grid: { left: '3%', right: '6%', top: 50, bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { interval: 0, rotate: labels.length > 8 ? 30 : 0 } },
    yAxis: [
      { type: 'value', name: metricLabel(metric) },
      { type: 'value', name: '累计占比(%)', min: 0, max: 100, axisLabel: { formatter: '{value}%' } }
    ],
    series: [
      {
        name: metricLabel(metric),
        type: 'bar',
        data: values,
        barMaxWidth: 32,
        itemStyle: { color: CHART_COLORS[0] }
      },
      {
        name: '累计占比',
        type: 'line',
        yAxisIndex: 1,
        data: cumulative,
        smooth: true,
        itemStyle: { color: CHART_COLORS[3] }
      }
    ]
  }
  if (labels.length > 20) {
    option.dataZoom = [
      { type: 'inside' },
      { type: 'slider', height: 16, bottom: 28 }
    ]
  }
  return option
}

function businessValues(item) {
  const overlay = toNumber(item.overlay)
  const packageChange = toNumber(item.package_change)
  return {
    overlay,
    package_change: packageChange,
    other: Math.max(0, toNumber(item.total) - overlay - packageChange)
  }
}

function lhValues(item) {
  const inbound = toNumber(item.inbound)
  const outbound = toNumber(item.outbound)
  return {
    inbound,
    outbound,
    unknown: Math.max(0, toNumber(item.total) - inbound - outbound)
  }
}

function validValues(item) {
  return {
    overlay_day: toNumber(item.overlay_day),
    overlay_month: toNumber(item.overlay_month),
    overlay_long: toNumber(item.overlay_long),
    overlay_undefined: toNumber(item.overlay_undefined)
  }
}

const CROSS_DEFINITIONS = {
  business: {
    names: ['叠加包', '套餐变更', '其他'],
    keys: ['overlay', 'package_change', 'other'],
    values: businessValues
  },
  lh: {
    names: ['来话', '去话', '未标注'],
    keys: ['inbound', 'outbound', 'unknown'],
    values: lhValues
  },
  valid: {
    names: ['日包', '月包', '长期包', '未定义'],
    keys: ['overlay_day', 'overlay_month', 'overlay_long', 'overlay_undefined'],
    values: validValues
  }
}

export function buildCrossData(items = [], {
  kind = 'business',
  limit = 10,
  labelKey = 'displayName',
  sortMetric = 'total'
} = {}) {
  const definition = CROSS_DEFINITIONS[kind]
  if (!definition) return { categories: [], series: [] }
  const top = [...items]
    .map(item => ({
      ...item,
      _label: item[labelKey] || item.displayName || item.label || item.name || item.team || item.group_name || item.product_name || item.product_id || '',
      _sort: metricValue(item, sortMetric)
    }))
    .sort((a, b) => b._sort - a._sort)
    .slice(0, limit)

  return {
    categories: top.map(item => item._label),
    series: definition.names.map((name, index) => {
      const key = definition.keys[index]
      return {
        name,
        data: top.map(item => round(definition.values(item)[key]))
      }
    })
  }
}

export function buildBusinessCrossOptions(items = [], options = {}) {
  const { categories, series } = buildCrossData(items, { ...options, kind: 'business' })
  return createStackedBarOptions(categories, series, options.title || '业务结构', {
    rotate: categories.length > 8 ? 30 : 0
  })
}

export function buildLhCrossOptions(items = [], options = {}) {
  const { categories, series } = buildCrossData(items, { ...options, kind: 'lh' })
  return createStackedBarOptions(categories, series, options.title || '来话/去话结构', {
    rotate: categories.length > 8 ? 30 : 0
  })
}

export function buildValidCrossOptions(items = [], options = {}) {
  const { categories, series } = buildCrossData(items, { ...options, kind: 'valid' })
  return createStackedBarOptions(categories, series, options.title || '叠加包有效期结构', {
    rotate: categories.length > 8 ? 30 : 0
  })
}

export function buildDailyTrendOptions(days = []) {
  const categories = days.map(item => item.date)
  const series = [
    { name: '产品办理量', data: days.map(item => toNumber(item.total)) },
    { name: '订单数', data: days.map(item => toNumber(item.order_count)) },
    { name: '来话', data: days.map(item => toNumber(item.inbound)) },
    { name: '去话', data: days.map(item => toNumber(item.outbound)) },
    { name: '叠加包', data: days.map(item => toNumber(item.overlay)) },
    { name: '套餐变更', data: days.map(item => toNumber(item.package_change)) }
  ]
  return createMultiLineOptions(categories, series, '每日办理趋势', {
    yName: '数量',
    dataZoom: days.length > 20
  })
}

export function buildDailyBusinessOptions(days = []) {
  const categories = days.map(item => item.date)
  const series = [
    { name: '叠加包', data: days.map(item => toNumber(item.overlay)) },
    { name: '套餐变更', data: days.map(item => toNumber(item.package_change)) },
    {
      name: '其他',
      data: days.map(item => {
        const values = businessValues(item)
        return values.other
      })
    }
  ]
  return createStackedBarOptions(categories, series, '每日业务结构', {
    rotate: categories.length > 15 ? 30 : 0,
    tooltipFormatter: params => dailyTooltip(params, days)
  })
}

export function buildDailyLhOptions(days = []) {
  const categories = days.map(item => item.date)
  const series = [
    { name: '来话', data: days.map(item => toNumber(item.inbound)) },
    { name: '去话', data: days.map(item => toNumber(item.outbound)) },
    {
      name: '未标注',
      data: days.map(item => lhValues(item).unknown)
    }
  ]
  return createStackedBarOptions(categories, series, '每日来话/去话结构', {
    rotate: categories.length > 15 ? 30 : 0,
    tooltipFormatter: params => dailyTooltip(params, days)
  })
}

export function buildDailyValidOptions(days = []) {
  const categories = days.map(item => item.date)
  const series = [
    { name: '日包', data: days.map(item => toNumber(item.overlay_day)) },
    { name: '月包', data: days.map(item => toNumber(item.overlay_month)) },
    { name: '长期包', data: days.map(item => toNumber(item.overlay_long)) },
    { name: '未定义', data: days.map(item => toNumber(item.overlay_undefined)) }
  ]
  return createStackedBarOptions(categories, series, '每日叠加包有效期结构', {
    rotate: categories.length > 15 ? 30 : 0,
    tooltipFormatter: params => dailyTooltip(params, days)
  })
}

export function buildDailyOrderRateOptions(days = []) {
  const categories = days.map(item => item.date)
  const values = days.map(item => {
    const total = toNumber(item.total)
    return total ? round((toNumber(item.order_count) / total) * 100) : 0
  })
  return createMultiLineOptions(categories, [{
    name: '订单覆盖率',
    data: values
  }], '每日订单覆盖率', {
    yName: '%',
    dataZoom: days.length > 20
  })
}

function dailyTooltip(params, days) {
  const list = Array.isArray(params) ? params : [params]
  if (!list.length) return ''
  const date = list[0]?.axisValue || ''
  const day = days.find(item => item.date === date)
  if (!day) return list.map(item => `${item.marker}${item.seriesName}：${item.value}`).join('\n')
  const lines = [
    date,
    `产品办理量：${toNumber(day.total).toLocaleString('zh-CN')}`,
    `订单数：${toNumber(day.order_count).toLocaleString('zh-CN')}`,
    ...list.map(item => `${item.marker}${item.seriesName}：${toNumber(item.value).toLocaleString('zh-CN')}`)
  ]
  return lines.join('\n')
}

export function buildTeamScatterOptions(teams = [], { title = '班组人均效率分布' } = {}) {
  const items = enrichTeams(teams)
  const data = items.map(item => {
    const people = toNumber(item.people)
    const avgTotal = people ? toNumber(item.total) / people : 0
    const orderRate = toNumber(item.total) ? (toNumber(item.order_count) / toNumber(item.total)) * 100 : 0
    return {
      ...item,
      name: item.team,
      value: [round(avgTotal), round(orderRate), people]
    }
  })
  const maxPeople = Math.max(1, ...data.map(item => item.value[2]))
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'item',
      confine: false,
      appendToBody: true,
      extraCssText: 'white-space: pre-line; max-width: 320px; z-index: 99999;',
      formatter: params => {
        const item = params.data || {}
        return [
          item.team,
          item.leader ? `组长：${item.leader}` : '',
          `人数：${toNumber(item.people)}`,
          `人均办理量：${formatMetricValue(item.value?.[0], 'avg_total')}`,
          `订单覆盖率：${formatMetricValue(item.value?.[1], 'order_rate')}`,
          `办理量：${toNumber(item.total).toLocaleString('zh-CN')}`,
          `订单数：${toNumber(item.order_count).toLocaleString('zh-CN')}`
        ].filter(Boolean).join('\n')
      }
    },
    grid: { left: '3%', right: '6%', top: 50, bottom: '12%', containLabel: true },
    xAxis: { type: 'value', name: '人均办理量' },
    yAxis: { type: 'value', name: '订单覆盖率(%)', axisLabel: { formatter: '{value}%' } },
    series: [{
      type: 'scatter',
      data,
      symbolSize: value => {
        const people = toNumber(value?.[2])
        return 8 + (people / maxPeople) * 22
      },
      itemStyle: { color: CHART_COLORS[4] }
    }]
  }
}

export function buildEmployeeScatterOptions(employees = [], { title = '员工办理量与订单数分布', limit = 50 } = {}) {
  const items = enrichEmployees(employees)
    .sort((a, b) => toNumber(b.total) - toNumber(a.total))
    .slice(0, limit)
  const data = items.map(item => ({
    ...item,
    name: item.displayName,
    value: [toNumber(item.total), toNumber(item.order_count)]
  }))
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'item',
      confine: false,
      appendToBody: true,
      extraCssText: 'white-space: pre-line; max-width: 320px; z-index: 99999;',
      formatter: params => {
        const item = params.data || {}
        return [
          item.displayName,
          `工号：${item.kf_id || '-'}`,
          `班组：${item.team || '-'}`,
          `行分类：${item.group_name || '-'}`,
          `办理量：${toNumber(item.total).toLocaleString('zh-CN')}`,
          `订单数：${toNumber(item.order_count).toLocaleString('zh-CN')}`,
          `订单覆盖率：${formatMetricValue(metricValue(item, 'order_rate'), 'order_rate')}`
        ].join('\n')
      }
    },
    grid: { left: '3%', right: '6%', top: 50, bottom: '12%', containLabel: true },
    xAxis: { type: 'value', name: '产品办理量' },
    yAxis: { type: 'value', name: '订单数' },
    series: [{
      type: 'scatter',
      data,
      symbolSize: 10,
      itemStyle: { color: CHART_COLORS[0] }
    }]
  }
}

export function buildTeamRadarOptions(teams = [], { limit = 8 } = {}) {
  const items = enrichTeams(teams)
    .sort((a, b) => toNumber(b.total) - toNumber(a.total))
    .slice(0, limit)
  const indicators = [
    { name: '办理量', max: Math.max(1, ...items.map(item => toNumber(item.total))) },
    { name: '订单数', max: Math.max(1, ...items.map(item => toNumber(item.order_count))) },
    { name: '来话', max: Math.max(1, ...items.map(item => toNumber(item.inbound))) },
    { name: '去话', max: Math.max(1, ...items.map(item => toNumber(item.outbound))) },
    { name: '叠加包', max: Math.max(1, ...items.map(item => toNumber(item.overlay))) },
    { name: '套餐变更', max: Math.max(1, ...items.map(item => toNumber(item.package_change))) }
  ]
  return {
    title: { text: '班组多指标雷达', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll' },
    radar: { indicator: indicators, radius: '58%' },
    series: [{
      type: 'radar',
      data: items.map((item, index) => ({
        name: item.team,
        value: [
          toNumber(item.total),
          toNumber(item.order_count),
          toNumber(item.inbound),
          toNumber(item.outbound),
          toNumber(item.overlay),
          toNumber(item.package_change)
        ],
        itemStyle: { color: CHART_COLORS[index % CHART_COLORS.length] }
      }))
    }]
  }
}
