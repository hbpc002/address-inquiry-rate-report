import { CHART_COLORS } from './echarts'

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

export function buildScatterOptions(items) {
  const teamMap = buildTeamMap(items)
  const teamNames = Object.keys(teamMap)

  const series = teamNames.map(team => {
    const color = CHART_COLORS[teamMap[team] % CHART_COLORS.length]
    return {
      name: team,
      type: 'scatter',
      symbolSize: 12,
      data: items.filter(item => teamName(item) === team).map(toPoint),
      itemStyle: { color, opacity: 0.8 },
      label: {
        show: true,
        fontSize: 13,
        fontWeight: 600,
        color,
        position: 'top',
        distance: 4,
        textBorderColor: 'rgba(255,255,255,0.85)',
        textBorderWidth: 2,
        formatter: (params) => (params.data ?? params.value)?.[2]?.name ?? ''
      },
      labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' }
    }
  })

  return {
    title: {
      text: '推荐量-成功率散点图（可滚轮缩放，以鼠标为中心）',
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
    grid: { left: '12%', right: 70, bottom: 90, top: 50, containLabel: true },
    xAxis: { type: 'value', name: '推荐量', axisLabel: { rotate: 0 } },
    yAxis: { type: 'value', name: '成功率(%)', min: 0, max: 100 },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, yAxisIndex: 0, zoomOnMouseWheel: true, moveOnMouseMove: true },
      { type: 'slider', xAxisIndex: 0, height: 16, bottom: 30 },
      { type: 'slider', yAxisIndex: 0, orient: 'vertical', width: 14, right: 8, top: 30, bottom: 30 }
    ],
    series
  }
}