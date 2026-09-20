import { CHART_COLORS } from './echarts'

export const SHOW_ALL_LABEL_THRESHOLD = 20
export const TOP_LABEL_COUNT = 12
export const ZOOM_THRESHOLD = 60

export function teamName(item) {
  return item.team || '未知班组'
}

export function toPoint(item) {
  return [item.recommend, +((item.success_rate || 0) * 100).toFixed(1), {
    emp_no: item.emp_no,
    name: item.name,
    team: item.team,
    recommend: item.recommend,
    completed: item.completed
  }]
}

export function buildTeamMap(items) {
  const map = {}
  items.forEach(item => {
    const team = teamName(item)
    if (!(team in map)) map[team] = Object.keys(map).length
  })
  return map
}

// 人数少时给所有人标姓名；人数多时只给推荐量 Top N 标姓名
//（同推荐量按成功率降序、姓名升序）
export function selectLabeledItems(items) {
  if (items.length <= SHOW_ALL_LABEL_THRESHOLD) return items
  return [...items]
    .sort((a, b) =>
      (b.recommend - a.recommend)
      || ((b.success_rate || 0) - (a.success_rate || 0))
      || String(a.name || '').localeCompare(String(b.name || ''))
    )
    .slice(0, TOP_LABEL_COUNT)
}

export function buildScatterOptions(items) {
  const teamMap = buildTeamMap(items)
  const labeled = selectLabeledItems(items)
  const teamNames = Object.keys(teamMap)

  const series = teamNames.map(team => ({
    name: team,
    type: 'scatter',
    symbolSize: 12,
    data: items.filter(item => teamName(item) === team).map(toPoint),
    itemStyle: { color: CHART_COLORS[teamMap[team] % CHART_COLORS.length], opacity: 0.8 }
  }))

  const labelSeries = {
    name: '',
    type: 'scatter',
    symbol: 'circle',
    symbolSize: 0,
    silent: true,
    data: labeled.map(toPoint),
    label: {
      show: true,
      fontSize: 9,
      color: '#333',
      position: 'top',
      distance: 3,
      formatter: (params) => (params.data ?? params.value)?.[2]?.name ?? ''
    },
    labelLayout: { hideOverlap: true }
  }

  const zoomEnabled = items.length > ZOOM_THRESHOLD

  const options = {
    title: {
      text: zoomEnabled ? '推荐量-成功率散点图（人数较多，可滚轮缩放）' : '推荐量-成功率散点图',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params) => {
        const meta = params.data?.[2] || {}
        const x = params.data?.[0]
        const y = params.data?.[1]
        return `${meta.name || ''} (${meta.emp_no || ''})\n${meta.team || ''}\n推荐量: ${x ?? 0}\n成功率: ${(y ?? 0).toFixed(1)}%\n成功推荐: ${meta.completed ?? 0}`
      }
    },
    legend: { orient: 'horizontal', bottom: 0, data: teamNames },
    grid: { left: '3%', right: '4%', bottom: zoomEnabled ? 90 : '12%', containLabel: true },
    xAxis: { type: 'value', name: '推荐量', axisLabel: { rotate: 0 } },
    yAxis: { type: 'value', name: '成功率(%)', min: 0, max: 100 },
    series: [...series, labelSeries]
  }

  if (zoomEnabled) {
    options.dataZoom = [
      { type: 'inside', xAxisIndex: 0, yAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, height: 16, bottom: 30 }
    ]
  }

  return options
}