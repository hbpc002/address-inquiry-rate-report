import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('../src/stores/user', () => {
  const get = vi.fn()
  return {
    api: { get },
    useUserStore: vi.fn(() => ({ hasPermission: vi.fn(() => true) }))
  }
})

vi.mock('../src/stores/uiConfig', () => ({
  useUiConfigStore: vi.fn(() => ({
    labels: { marketing_opening_report: '开口率报表' },
    loaded: true
  }))
}))

vi.mock('../src/utils/download', () => ({ downloadBlob: vi.fn() }))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn() }
}))

import { api } from '../src/stores/user'
import { downloadBlob } from '../src/utils/download'
import MarketingOpeningReport from '../src/views/MarketingOpeningReport.vue'

const columns = [
  { key: 'active_overlay', product: '叠加包', action: '主动', label: '叠加包主动开口量' },
  { key: 'opened_overlay', product: '叠加包', action: '已开口', label: '叠加包已开口量' },
  { key: 'active_broadband', product: '宽带', action: '主动', label: '宽带主动开口量' },
  { key: 'opened_broadband', product: '宽带', action: '已开口', label: '宽带已开口量' },
  { key: 'active_mobile_new', product: '移网新装', action: '主动', label: '移网新装主动开口量' },
  { key: 'opened_mobile_new', product: '移网新装', action: '已开口', label: '移网新装已开口量' },
  { key: 'active_terminal', product: '终端', action: '主动', label: '终端主动开口量' },
  { key: 'opened_terminal', product: '终端', action: '已开口', label: '终端已开口量' },
  { key: 'active_package', product: '套餐', action: '主动', label: '套餐主动开口量' },
  { key: 'opened_package', product: '套餐', action: '已开口', label: '套餐已开口量' }
]

const baseMetric = {
  contact_count: 4,
  opened_count: 2,
  opening_rate: 0.5,
  active_overlay: 2,
  opened_overlay: 1,
  active_broadband: 1,
  opened_broadband: 1,
  active_mobile_new: 0,
  opened_mobile_new: 0,
  active_terminal: 0,
  opened_terminal: 0,
  active_package: 2,
  opened_package: 1
}

const reportData = {
  stats: { ...baseMetric, people_count: 2, start_date: '2026-11-01', end_date: '2026-11-30' },
  columns,
  employees: [
    { kf_id: 'KF001', name: '张三', team: '热线1组', dept: '客服部', dept_group: '一组', class_name: '热线', ...baseMetric },
    { kf_id: 'KF002', name: '李四', team: '区域2组', dept: '客服部', dept_group: '一组', class_name: '区域', ...baseMetric, contact_count: 2, opened_count: 1, opening_rate: 0.5 }
  ],
  teams: [
    { dept_group: '一组', dept: '客服部', team: '热线1组', people: 1, ...baseMetric }
  ],
  classes: [
    { dept_group: '一组', dept: '客服部', class_name: '热线', people: 1, ...baseMetric }
  ],
  days: [
    { date: '2026-11-02', people: 2, ...baseMetric }
  ],
  options: { teams: ['热线1组', '区域2组'], classes: ['热线', '区域'], department_groups: ['一组'] }
}

const stubs = {
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button><slot /></button>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-radio-group': { template: '<div><slot /></div>' },
  'el-radio': { template: '<label><slot /></label>' },
  'el-date-picker': { template: '<input />' },
  'el-select': { template: '<div><slot /></div>' },
  'el-option': { template: '<div />' },
  'el-input': { template: '<input />' },
  'el-row': { template: '<div><slot /></div>' },
  'el-statistic': { template: '<div class="stat-stub" />' },
  'el-tabs': { template: '<div><slot /></div>' },
  'el-tab-pane': { template: '<div />' },
  'el-table': { template: '<table><slot /></table>' },
  'el-table-column': {
    props: {
      prop: String,
      label: String,
      sortable: { type: Boolean, default: false }
    },
    template: '<col :data-prop="prop != null ? String(prop) : \'\'" :data-label="label != null ? String(label) : \'\'" :data-sortable="sortable ? \'true\' : \'false\'" />'
  }
}

async function mountPage() {
  const wrapper = mount(MarketingOpeningReport, { global: { stubs } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('开口率报表', () => {
  beforeEach(() => {
    api.get.mockReset()
    downloadBlob.mockReset()
    api.get.mockResolvedValue({ data: reportData })
  })

  it('加载统计卡片、员工数据和O-X十列', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState
    expect(api.get).toHaveBeenCalledWith('/marketing-openings/report', { params: expect.any(Object) })
    expect(state.openingColumns).toHaveLength(10)
    expect(state.openingColumns[0].label).toBe('叠加包主动')
    expect(state.tableData).toHaveLength(2)
    expect(state.statsRate).toBe(50)
    expect(state.formatRate(null)).toBe('-')
    expect(state.formatRate(0.5)).toBe('50.00%')
  })

  it('按当前维度导出报表', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState
    state.dimension = 'team'
    state.handleExport()
    expect(downloadBlob).toHaveBeenCalledWith(
      '/marketing-openings/report/export',
      expect.objectContaining({ dimension: 'team' }),
      '开口率报表.csv'
    )
  })
})
