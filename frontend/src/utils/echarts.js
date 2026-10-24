import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, RadarChart, ScatterChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  DataZoomComponent,
  MarkPointComponent,
  MarkLineComponent,
  RadarComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  DataZoomComponent,
  BarChart,
  LineChart,
  PieChart,
  RadarChart,
  ScatterChart,
  MarkPointComponent,
  MarkLineComponent,
  RadarComponent,
  CanvasRenderer
])

export default echarts

export const CHART_COLORS = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff5722'
]

export function createPieOptions(data, title, colors = CHART_COLORS, unit = '工时', tooltipFormatter = null) {
  const options = {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'item',
      confine: true,
      extraCssText: 'white-space: pre-line; max-width: 320px; z-index: 9999;',
      formatter: (params) => {
        let extra = ''
        if (params.data.peopleCount !== undefined) extra += `人数: ${params.data.peopleCount}\n`
        if (params.data.avgHours !== undefined) extra += `人均工时: ${params.data.avgHours}h\n`
        if (params.data.avgDuration !== undefined) extra += `平均通话均长: ${params.data.avgDuration}s\n`
        if (params.data.totalTicket !== undefined) extra += `工单总量: ${params.data.totalTicket}\n`
        if (params.data.tiDanLv !== undefined) extra += `提单率: ${(params.data.tiDanLv * 100).toFixed(2)}%\n`
        return `${params.name}\n${unit}: ${params.value} (${params.percent}%)\n${extra}`
      }
    },
    legend: { orient: 'horizontal', bottom: 0 },
    series: [{
      type: 'pie',
      radius: '60%',
      data: data.map((item, i) => ({ ...item, itemStyle: { color: colors[i % colors.length] } })),
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
      label: { formatter: '{b}: {c}' }
    }]
  }
  applyTooltipFormatter(options.tooltip, tooltipFormatter)
  return options
}

function applyTooltipFormatter(tooltip, formatter) {
  if (!formatter) return
  tooltip.confine = false
  tooltip.appendToBody = true
  tooltip.extraCssText = 'white-space: pre-line; max-width: 520px; z-index: 99999;'
  tooltip.formatter = formatter
}

export function createBarOptions(xData, yData, title, xName = '', yName = '', tooltipFormatter = null) {
  const options = {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: [yName], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: xData, name: xName },
    yAxis: { type: 'value', name: yName },
    series: [{ name: yName, type: 'bar', data: yData, itemStyle: { color: CHART_COLORS[0] } }]
  }
  applyTooltipFormatter(options.tooltip, tooltipFormatter)
  return options
}

export function createLineOptions(xData, yData, title, xName = '', yName = '') {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: [yName], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: xData, name: xName },
    yAxis: { type: 'value', name: yName },
    series: [{ name: yName, type: 'line', data: yData, smooth: true, itemStyle: { color: CHART_COLORS[1] }, areaStyle: { opacity: 0.3 } }]
  }
}

export function createHorizontalBarOptions(yData, xData, title, yName = '', xName = '', tooltipFormatter = null) {
  const options = {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '12%', right: '8%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', name: xName },
    yAxis: { type: 'category', data: yData, name: yName },
    series: [{ type: 'bar', data: xData, itemStyle: { color: CHART_COLORS[2] }, label: { show: true, position: 'right' } }]
  }
  applyTooltipFormatter(options.tooltip, tooltipFormatter)
  return options
}

export function createMultiBarOptions(categories, series, title, tooltipFormatter = null) {
  const options = {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(s => s.name), bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: categories },
    yAxis: { type: 'value' },
    series: series.map((s, i) => ({ ...s, type: 'bar', itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] } }))
  }
  applyTooltipFormatter(options.tooltip, tooltipFormatter)
  return options
}

export function createStackedBarOptions(categories, series, title, options = {}) {
  const {
    horizontal = false,
    stack = 'total',
    tooltipFormatter = null,
    showLegend = true,
    dataZoom = false,
    xName = '',
    yName = '',
    rotate = 0,
    showLabel = false,
    colors = CHART_COLORS
  } = options

  const categoryAxis = {
    type: 'category',
    data: categories,
    name: horizontal ? yName : xName,
    axisLabel: { interval: 0, rotate }
  }
  const valueAxis = { type: 'value', name: horizontal ? xName : yName }

  const option = {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: showLegend ? { data: series.map(s => s.name), bottom: 0, type: 'scroll' } : undefined,
    grid: {
      left: '3%',
      right: '4%',
      top: 50,
      bottom: showLegend ? (dataZoom ? '20%' : '15%') : '6%',
      containLabel: true
    },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? categoryAxis : valueAxis,
    series: series.map((s, i) => ({
      name: s.name,
      type: 'bar',
      stack: s.stack || stack,
      data: s.data,
      barMaxWidth: 36,
      itemStyle: { color: s.color || colors[i % colors.length] },
      label: showLabel ? { show: true, position: horizontal ? 'right' : 'inside' } : undefined
    }))
  }
  if (dataZoom) {
    option.dataZoom = [
      { type: 'inside', xAxisIndex: horizontal ? undefined : 0, yAxisIndex: horizontal ? 0 : undefined },
      { type: 'slider', height: 16, bottom: showLegend ? 28 : 4, xAxisIndex: horizontal ? undefined : 0, yAxisIndex: horizontal ? 0 : undefined }
    ]
  }
  applyTooltipFormatter(option.tooltip, tooltipFormatter)
  return option
}

export function createMultiLineOptions(categories, series, title, options = {}) {
  const {
    tooltipFormatter = null,
    xName = '',
    yName = '',
    showSymbol = false,
    area = false,
    showLegend = true,
    dataZoom = categories.length > 20,
    colors = CHART_COLORS
  } = options

  const option = {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: showLegend ? { data: series.map(s => s.name), bottom: 0, type: 'scroll' } : undefined,
    grid: {
      left: '3%',
      right: '4%',
      top: 50,
      bottom: showLegend ? (dataZoom ? '20%' : '15%') : '6%',
      containLabel: true
    },
    xAxis: { type: 'category', boundaryGap: false, data: categories, name: xName },
    yAxis: { type: 'value', name: yName },
    series: series.map((s, i) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      showSymbol,
      connectNulls: true,
      itemStyle: { color: s.color || colors[i % colors.length] },
      lineStyle: { width: 2 },
      areaStyle: area || s.area ? { opacity: 0.12 } : undefined
    }))
  }
  if (dataZoom) {
    option.dataZoom = [
      { type: 'inside' },
      { type: 'slider', height: 16, bottom: showLegend ? 28 : 4 }
    ]
  }
  applyTooltipFormatter(option.tooltip, tooltipFormatter)
  return option
}
