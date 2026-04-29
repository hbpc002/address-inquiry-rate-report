import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  DataZoomComponent,
  MarkPointComponent,
  MarkLineComponent
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
  MarkPointComponent,
  MarkLineComponent,
  CanvasRenderer
])

export default echarts

export const CHART_COLORS = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff5722'
]

export function createPieOptions(data, title, colors = CHART_COLORS) {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'horizontal', bottom: 0 },
    series: [{
      type: 'pie',
      radius: '60%',
      data: data.map((item, i) => ({ value: item.value, name: item.name, itemStyle: { color: colors[i % colors.length] } })),
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
      label: { formatter: '{b}: {c}' }
    }]
  }
}

export function createBarOptions(xData, yData, title, xName = '', yName = '') {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: [yName], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: xData, name: xName },
    yAxis: { type: 'value', name: yName },
    series: [{ name: yName, type: 'bar', data: yData, itemStyle: { color: CHART_COLORS[0] } }]
  }
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

export function createHorizontalBarOptions(yData, xData, title, yName = '', xName = '') {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '12%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', name: xName },
    yAxis: { type: 'category', data: yData, name: yName },
    series: [{ type: 'bar', data: xData, itemStyle: { color: CHART_COLORS[2] }, label: { show: true, position: 'right' } }]
  }
}

export function createMultiBarOptions(categories, series, title) {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(s => s.name), bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: categories },
    yAxis: { type: 'value' },
    series: series.map((s, i) => ({ ...s, type: 'bar', itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] } }))
  }
}
