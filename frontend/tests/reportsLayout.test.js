import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('../src/stores/user', () => {
  const get = vi.fn()
  return {
    api: { get },
    useUserStore: vi.fn(() => ({
      hasPermission: vi.fn(() => true)
    }))
  }
})

vi.mock('../src/utils/echarts', () => ({
  createPieOptions: vi.fn(() => ({})),
  createBarOptions: vi.fn(() => ({})),
  createLineOptions: vi.fn(() => ({})),
  createHorizontalBarOptions: vi.fn(() => ({})),
  createMultiBarOptions: vi.fn(() => ({})),
  CHART_COLORS: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
}))

vi.mock('../src/components/Echart.vue', () => ({
  default: {
    name: 'Echart',
    props: ['options', 'height'],
    template: '<div class="echart-stub" data-echart :data-height="height || \'400px\'"></div>'
  }
}))

vi.mock('../src/components/ColumnWithTip.vue', () => ({
  default: { name: 'ColumnWithTip', template: '<span class="column-with-tip-stub" />' }
}))

vi.mock('../src/components/FieldFilterPanel.vue', () => ({
  default: { name: 'FieldFilterPanel', template: '<button class="field-filter-stub">字段筛选</button>' }
}))

import { api } from '../src/stores/user'
import Reports from '../src/views/Reports.vue'

const dailyItems = [
  { emp_id: 1, dept: '客服中心', status: '正常' },
  { emp_id: 2, dept: '客服中心', status: '迟到' }
]

const stubs = {
  'el-button': { template: '<button class="el-button-stub"><slot /></button>' },
  'el-card': { template: '<div class="el-card-stub"><slot name="header" /><slot /></div>' },
  'el-col': {
    props: ['span'],
    template: '<div class="el-col-stub" :data-span="span != null ? String(span) : \'\'"><slot /></div>'
  },
  'el-date-picker': { template: '<input type="text" class="el-date-picker-stub" />' },
  'el-dialog': { props: ['modelValue'], template: '<div v-if="modelValue" class="el-dialog-stub"><slot /></div>' },
  'el-empty': { template: '<div class="el-empty-stub"><slot /></div>' },
  'el-form': { template: '<form class="el-form-stub"><slot /></form>' },
  'el-form-item': { props: ['label'], template: '<div class="el-form-item-stub"><span class="el-form-item-label">{{ label }}</span><slot /></div>' },
  'el-input': { template: '<input type="text" class="el-input-stub" />' },
  'el-option': { template: '<div class="el-option-stub" />' },
  'el-pagination': { template: '<div class="el-pagination-stub" />' },
  'el-radio-button': { template: '<label class="el-radio-button-stub"><slot /></label>' },
  'el-radio-group': { template: '<div class="el-radio-group-stub"><slot /></div>' },
  'el-row': { template: '<div class="el-row-stub"><slot /></div>' },
  'el-select': { template: '<div class="el-select-stub"><slot /></div>' },
  'el-space': { template: '<div class="el-space-stub"><slot /></div>' },
  'el-statistic': {
    props: ['title', 'value', 'precision'],
    template: '<div class="el-statistic-stub" :data-title="title"><span class="stat-title">{{ title }}</span><span class="stat-value">{{ value != null ? String(value) : \'\' }}</span><slot name="suffix" /></div>'
  },
  'el-table': { template: '<table class="el-table-stub"><slot /></table>' },
  'el-table-column': { template: '<col class="el-table-column-stub" />' },
  'el-tab-pane': { template: '<div class="el-tab-pane-stub"><slot /></div>' },
  'el-tabs': { template: '<div class="el-tabs-stub"><slot /></div>' },
  'el-tag': { template: '<span class="el-tag-stub"><slot /></span>' }
}

async function mountPage() {
  const wrapper = mount(Reports, {
    global: { stubs }
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('Reports 考勤报表 - 指标区单行压缩', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    api.get.mockImplementation((url) => {
      if (url === '/employees/teams') return Promise.resolve({ data: [] })
      if (url === '/checkins/departments') return Promise.resolve({ data: [] })
      if (url === '/reports/daily') return Promise.resolve({ data: { items: dailyItems, total: dailyItems.length } })
      if (url === '/field-annotations/public') return Promise.resolve({ data: [] })
      return Promise.resolve({ data: [] })
    })
  })

  it('日报表统计行 7 个指标均采用 span=3', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('.stats-row')
    const dailyCols = rows[0].findAll('.el-col-stub')
    expect(dailyCols).toHaveLength(7)
    dailyCols.forEach(col => {
      expect(col.attributes('data-span')).toBe('3')
    })
  })

  it('月度汇总统计行 6 个指标均采用 span=4', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('.stats-row')
    const monthlyCols = rows[1].findAll('.el-col-stub')
    expect(monthlyCols).toHaveLength(6)
    monthlyCols.forEach(col => {
      expect(col.attributes('data-span')).toBe('4')
    })
  })

  it('自定义时间段统计行 6 个指标均采用 span=4', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('.stats-row')
    const rangeCols = rows[2].findAll('.el-col-stub')
    expect(rangeCols).toHaveLength(6)
    rangeCols.forEach(col => {
      expect(col.attributes('data-span')).toBe('4')
    })
  })

  it('日报表指标标题与数值正确绑定', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('.stats-row')
    const dailyStats = rows[0].findAll('.el-statistic-stub')
    const titles = dailyStats.map(s => s.attributes('data-title'))
    expect(titles).toEqual(['应到人数', '出勤人数', '正常', '迟到', '缺勤', '休息', '出勤率'])
    expect(dailyStats[0].text()).toContain('2')
    expect(dailyStats[3].text()).toContain('1')
    expect(dailyStats[6].text()).toContain('100')
  })
})
