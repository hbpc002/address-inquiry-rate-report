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
  createHorizontalBarOptions: vi.fn(() => ({})),
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

vi.mock('html2canvas', () => ({ default: vi.fn(() => Promise.resolve({})) }))

import { api } from '../src/stores/user'
import WorkloadReport from '../src/views/WorkloadReport.vue'

const reportData = {
  stats: {
    total_people: 20,
    total_records: 30,
    total_call_count: 100,
    total_work_duration: 0,
    total_ticket_count: 10,
    total_outbound: 5,
    total_sat_numerator: 0,
    total_sat_denominator: 0
  },
  items: [
    {
      account: 'A001', name: '张三', emp_no: 'E001', team_desc: '班组A1', role: '组员',
      aggregated_metrics: {
        '呼入人工服务-人工服务-通话次数': 60,
        '呼入人工服务-人工服务-通话总时长(秒)': 3600,
        '呼入人工服务-满意度-非常满意量': 5,
        '呼入人工服务-满意度-满意量': 3,
        '呼入人工服务-满意度-一般量': 1,
        '呼入人工服务-满意度-不满意量': 1,
        '呼入人工服务-满意度-非常不满意量': 0
      }
    },
    {
      account: 'A002', name: '李四', emp_no: 'E002', team_desc: '班组A1', role: '组员',
      aggregated_metrics: {
        '呼入人工服务-人工服务-通话次数': 40,
        '呼入人工服务-人工服务-通话总时长(秒)': 2400,
        '呼入人工服务-满意度-非常满意量': 3,
        '呼入人工服务-满意度-满意量': 2,
        '呼入人工服务-满意度-一般量': 0,
        '呼入人工服务-满意度-不满意量': 0,
        '呼入人工服务-满意度-非常不满意量': 2
      }
    }
  ]
}

const stubs = {
  'el-button': { template: '<button class="el-button-stub"><slot /></button>' },
  'el-card': { template: '<div class="el-card-stub"><slot name="header" /><slot /></div>' },
  'el-checkbox': { template: '<label class="el-checkbox-stub"><slot /></label>' },
  'el-checkbox-group': { template: '<div class="el-checkbox-group-stub"><slot /></div>' },
  'el-col': {
    props: ['span'],
    template: '<div class="el-col-stub" :data-span="span != null ? String(span) : \'\'"><slot /></div>'
  },
  'el-date-picker': { template: '<input type="text" class="el-date-picker-stub" />' },
  'el-descriptions': { template: '<div class="el-descriptions-stub"><slot /></div>' },
  'el-descriptions-item': { template: '<span class="el-descriptions-item-stub"><slot /></span>' },
  'el-dialog': { props: ['modelValue'], template: '<div v-if="modelValue" class="el-dialog-stub"><slot /></div>' },
  'el-drawer': { props: ['modelValue'], template: '<div v-if="modelValue" class="el-drawer-stub"><slot /></div>' },
  'el-form': { template: '<form class="el-form-stub"><slot /></form>' },
  'el-form-item': { props: ['label'], template: '<div class="el-form-item-stub"><span class="el-form-item-label">{{ label }}</span><slot /></div>' },
  'el-input': { template: '<input type="text" class="el-input-stub" />' },
  'el-input-number': { template: '<input type="number" class="el-input-number-stub" />' },
  'el-option': { template: '<div class="el-option-stub" />' },
  'el-pagination': { template: '<div class="el-pagination-stub" />' },
  'el-radio': { template: '<label class="el-radio-stub"><slot /></label>' },
  'el-radio-button': { template: '<label class="el-radio-button-stub"><slot /></label>' },
  'el-radio-group': { template: '<div class="el-radio-group-stub"><slot /></div>' },
  'el-row': { template: '<div class="el-row-stub"><slot /></div>' },
  'el-select': { template: '<div class="el-select-stub"><slot /></div>' },
  'el-statistic': {
    props: ['title', 'value', 'precision'],
    template: '<div class="el-statistic-stub" :data-title="title"><span class="stat-title">{{ title }}</span><span class="stat-value">{{ value != null ? String(value) : \'\' }}</span><slot name="suffix" /></div>'
  },
  'el-table': { template: '<table class="el-table-stub"><slot /></table>' },
  'el-table-column': { template: '<col class="el-table-column-stub" />' }
}

async function mountPage() {
  const wrapper = mount(WorkloadReport, {
    global: { stubs }
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('WorkloadReport 汇总页 - 指标区单行压缩', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    api.get.mockImplementation((url) => {
      if (url === '/salary-config') return Promise.resolve({ data: { items: [] } })
      if (url === '/employees/teams') return Promise.resolve({ data: [{ team: '班组A1' }] })
      if (url === '/employees/leaders') return Promise.resolve({ data: [] })
      if (url === '/workloads/metrics-fields') return Promise.resolve({ data: [] })
      if (url === '/workloads/report') return Promise.resolve({ data: reportData })
      if (url === '/workloads') return Promise.resolve({ data: { items: [] } })
      return Promise.resolve({ data: [] })
    })
  })

  it('统计行内 8 个指标均采用 span=3（合计 24 格，单行不换行）', async () => {
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
    const titles = stats.map(s => s.attributes('data-title'))
    expect(titles).toEqual(['总人数', '记录条数', '呼入通话量', '平均通话均长', '工单总量', '呼出量', '提单率(%)', '满意率(%)'])
    expect(stats[0].text()).toContain('20')
    expect(stats[2].text()).toContain('100')
    expect(stats[3].text()).toContain('60')
    expect(stats[6].text()).toContain('10')
  })
})
