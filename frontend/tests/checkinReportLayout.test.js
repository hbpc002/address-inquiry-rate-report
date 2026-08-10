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
import CheckinReport from '../src/views/CheckinReport.vue'

const mockReport = {
  stats: {
    total_checkins: 100,
    emp_count: 20,
    total_hours: 1600.5,
    avg_hours: 8.0,
    overtime_count: 3,
    undertime_count: 2
  },
  items: [
    {
      emp_no: 'E001', name: '张三', dept: '测试部门', team: '班组A',
      checkin_count: 10, total_hours: 85.5, hour_status: 'overtime',
      hour_status_text: '超时 (130%)',
      checkins: [{ checkin_time: '2024-01-01 09:00', checkout_time: '2024-01-01 18:00', duration: 9.0 }]
    },
    {
      emp_no: 'E002', name: '李四', dept: '测试部门', team: '班组A',
      checkin_count: 8, total_hours: 64.0, hour_status: 'undertime',
      hour_status_text: '过短 (77%)', checkins: []
    },
    {
      emp_no: 'E003', name: '王五', dept: '测试部门', team: '班组B',
      checkin_count: 12, total_hours: 80.0, hour_status: 'normal',
      hour_status_text: '正常 (100%)', checkins: []
    }
  ]
}

const stubs = {
  'el-tabs': { template: '<div class="el-tabs-stub"><slot /></div>' },
  'el-tab-pane': { template: '<div class="el-tab-pane-stub"><slot /></div>' },
  'el-card': { template: '<div class="el-card-stub"><slot name="header" /><slot /></div>' },
  'el-row': { template: '<div class="el-row-stub"><slot /></div>' },
  'el-col': {
    props: ['span'],
    template: '<div class="el-col-stub" :data-span="span != null ? String(span) : \'\'"><slot /></div>'
  },
  'el-statistic': {
    props: ['title', 'value', 'precision'],
    template: '<div class="el-statistic-stub" :data-title="title"><span class="stat-title">{{ title }}</span><span class="stat-value">{{ value != null ? String(value) : \'\' }}</span><slot name="suffix" /></div>'
  },
  'el-button': { template: '<button class="el-button-stub"><slot /></button>' },
  'el-form': { template: '<form class="el-form-stub"><slot /></form>' },
  'el-form-item': { props: ['label'], template: '<div class="el-form-item-stub"><span class="el-form-item-label">{{ label }}</span><slot /></div>' },
  'el-radio-group': { template: '<div class="el-radio-group-stub"><slot /></div>' },
  'el-radio': { template: '<label class="el-radio-stub"><slot /></label>' },
  'el-radio-button': { template: '<label class="el-radio-button-stub"><slot /></label>' },
  'el-date-picker': { template: '<input type="text" class="el-date-picker-stub" />' },
  'el-input': { template: '<input type="text" class="el-input-stub" />' },
  'el-select': { template: '<div class="el-select-stub"><slot /></div>' },
  'el-option': { template: '<div class="el-option-stub" />' },
  'el-tooltip': { template: '<span class="el-tooltip-stub"><slot /></span>' },
  'el-table': { template: '<table class="el-table-stub"><slot /></table>' },
  'el-table-column': { template: '<col class="el-table-column-stub" />' },
  'el-tag': { template: '<span class="el-tag-stub"><slot /></span>' },
  'el-pagination': { template: '<div class="el-pagination-stub" />' },
  'el-drawer': { props: ['modelValue'], template: '<div v-if="modelValue" class="el-drawer-stub"><slot /></div>' },
  'el-descriptions': { template: '<div class="el-descriptions-stub"><slot /></div>' },
  'el-descriptions-item': { template: '<span class="el-descriptions-item-stub"><slot /></span>' },
  'el-slider': { template: '<div class="el-slider-stub" />' },
  'el-input-number': { template: '<input type="number" class="el-input-number-stub" />' },
  'el-icon': { template: '<span class="el-icon-stub"><slot /></span>' }
}

function findButton(wrapper, text) {
  return wrapper.findAll('button').find(b => b.text().includes(text))
}

async function mountPage() {
  const wrapper = mount(CheckinReport, {
    global: { stubs }
  })
  await flushPromises()
  return wrapper
}

describe('CheckinReport 汇总页 - 搜索栏折叠', () => {
  beforeEach(() => {
    sessionStorage.clear()
    api.get.mockImplementation((url) => {
      if (url === '/employees/teams') return Promise.resolve({ data: [{ team: '班组A' }] })
      if (url === '/checkins/team-report') return Promise.resolve({ data: { items: [] } })
      if (url === '/checkins/time-analysis') return Promise.resolve({ data: {} })
      return Promise.resolve({ data: mockReport })
    })
  })

  it('默认折叠搜索栏（showSearch=false）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.section-search-area').element.style.display).toBe('none')
    expect(sessionStorage.getItem('checkin-report-show-search')).toBeNull()
  })

  it('点击“展开搜索”后搜索表单可见，再点击“收起搜索”恢复隐藏', async () => {
    const wrapper = await mountPage()
    const expand = findButton(wrapper, '展开搜索')
    expect(expand).toBeTruthy()
    await expand.trigger('click')
    expect(wrapper.find('.section-search-area').element.style.display).not.toBe('none')
    expect(sessionStorage.getItem('checkin-report-show-search')).toBe('true')

    const collapse = findButton(wrapper, '收起搜索')
    await collapse.trigger('click')
    expect(wrapper.find('.section-search-area').element.style.display).toBe('none')
    expect(sessionStorage.getItem('checkin-report-show-search')).toBe('false')
  })

  it('展开搜索后查询表单内容完整', async () => {
    const wrapper = await mountPage()
    await findButton(wrapper, '展开搜索').trigger('click')
    expect(wrapper.text()).toContain('按天')
    expect(wrapper.text()).toContain('日期')
    expect(wrapper.text()).toContain('班组')
    expect(wrapper.text()).toContain('查询')
  })
})

describe('CheckinReport 汇总页 - 图表区折叠与压缩', () => {
  beforeEach(() => {
    sessionStorage.clear()
    api.get.mockImplementation((url) => {
      if (url === '/employees/teams') return Promise.resolve({ data: [] })
      if (url === '/checkins/team-report') return Promise.resolve({ data: { items: [] } })
      if (url === '/checkins/time-analysis') return Promise.resolve({ data: {} })
      return Promise.resolve({ data: mockReport })
    })
  })

  it('默认展开图表（showCharts=true），汇总区渲染全部5个图表', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.summary-charts').exists()).toBe(true)
    expect(wrapper.findAll('.summary-charts .echart-stub')).toHaveLength(5)
  })

  it('点击“收起图表”后图表区整体移除，再次点击恢复', async () => {
    const wrapper = await mountPage()
    await findButton(wrapper, '收起图表').trigger('click')
    expect(wrapper.find('.summary-charts').exists()).toBe(false)
    expect(wrapper.findAll('.summary-charts .echart-stub')).toHaveLength(0)
    expect(sessionStorage.getItem('checkin-report-show-charts')).toBe('false')

    await findButton(wrapper, '展开图表').trigger('click')
    expect(wrapper.find('.summary-charts').exists()).toBe(true)
    expect(wrapper.findAll('.summary-charts .echart-stub')).toHaveLength(5)
    expect(sessionStorage.getItem('checkin-report-show-charts')).toBe('true')
  })

  it('收起图表后明细表仍存在于页面', async () => {
    const wrapper = await mountPage()
    await findButton(wrapper, '收起图表').trigger('click')
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
  })

  it('图表高度压缩为 180px/200px', async () => {
    const wrapper = await mountPage()
    const heights = wrapper.findAll('.summary-charts .echart-stub').map(e => e.attributes('data-height'))
    expect(heights).toEqual(['180px', '180px', '200px', '200px', '200px'])
  })

  it('切换会话期间记忆收起状态', async () => {
    sessionStorage.setItem('checkin-report-show-charts', 'false')
    const wrapper = await mountPage()
    expect(wrapper.find('.summary-charts').exists()).toBe(false)
  })
})

describe('CheckinReport 汇总页 - 指标区单行压缩', () => {
  beforeEach(() => {
    sessionStorage.clear()
    api.get.mockImplementation((url) => {
      if (url === '/checkins/team-report') return Promise.resolve({ data: { items: [] } })
      if (url === '/checkins/time-analysis') return Promise.resolve({ data: {} })
      return Promise.resolve({ data: mockReport })
    })
  })

  it('统计行内 8 个指标均采用 span=3（一共 24 格，单行不换行）', async () => {
    const wrapper = await mountPage()
    const statsRow = wrapper.find('.stats-row')
    const cols = statsRow.findAll('.el-col-stub')
    expect(cols).toHaveLength(8)
    cols.forEach(col => {
      expect(col.attributes('data-span')).toBe('3')
    })
  })

  it('指标标题与数值正确绑定', async () => {
    const wrapper = await mountPage()
    const stats = wrapper.findAll('.stats-row .el-statistic-stub')
    expect(stats[0].attributes('data-title')).toBe('签入人次')
    expect(stats[0].text()).toContain('100')
    expect(stats[4].attributes('data-title')).toBe('超时人数')
    expect(stats[4].text()).toContain('3')
  })
})