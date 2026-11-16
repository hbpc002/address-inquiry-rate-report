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
import MarketingOpeningReport from '../src/views/MarketingOpeningReport.vue'

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
  columns: [],
  employees: [
    { kf_id: 'KF001', name: '张三', team: '热线1组', dept: '客服部', dept_group: '一组', class_name: '热线', ...baseMetric },
    { kf_id: 'KF002', name: '李四', team: '区域2组', dept: '客服部', dept_group: '一组', class_name: '区域', ...baseMetric, contact_count: 2, opened_count: 1 }
  ],
  teams: [
    { dept_group: '一组', dept: '客服部', team: '热线1组', people: 2, ...baseMetric, contact_count: 6, opened_count: 3, opening_rate: 0.5 }
  ],
  classes: [
    { dept_group: '一组', dept: '客服部', class_name: '热线', people: 2, ...baseMetric, contact_count: 6, opened_count: 3, opening_rate: 0.5 }
  ],
  days: [
    { date: '2026-11-02', people: 2, ...baseMetric, contact_count: 6, opened_count: 3, opening_rate: 0.5 }
  ],
  options: { teams: ['热线1组', '区域2组'], classes: ['热线', '区域'], department_groups: ['一组'] }
}

const stubs = {
  'el-card': { template: '<div class="el-card-stub"><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button><slot /></button>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-radio-group': { template: '<div class="el-radio-group-stub"><slot /></div>' },
  'el-radio': { template: '<label><slot /></label>' },
  'el-radio-button': { template: '<label class="el-radio-button-stub"><slot /></label>' },
  'el-date-picker': { template: '<input />' },
  'el-select': { template: '<div><slot /></div>' },
  'el-option': { template: '<div />' },
  'el-input': { template: '<input />' },
  'el-row': { template: '<div class="el-row-stub"><slot /></div>' },
  'el-col': { template: '<div class="el-col-stub"><slot /></div>' },
  'el-statistic': { template: '<div class="stat-stub" />' },
  'el-tabs': { template: '<div><slot /></div>' },
  'el-tab-pane': { template: '<div />' },
  'el-pagination': { template: '<div class="pagination-stub" />' },
  'el-table': { template: '<table><slot /></table>' },
  'el-table-column': {
    props: {
      prop: String,
      label: String,
      sortable: { type: [Boolean, String], default: false }
    },
    template: '<col :data-prop="prop != null ? String(prop) : \'\'" :data-label="label != null ? String(label) : \'\'" :data-sortable="sortable ? \'true\' : \'false\'" />'
  },
  Echart: {
    props: ['options', 'height'],
    template: '<div class="echart-stub" :data-height="height" :data-title="options && options.title ? options.title.text : \'\'"></div>'
  }
}

async function mountPage() {
  const wrapper = mount(MarketingOpeningReport, { global: { stubs } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

function chartTitles(wrapper) {
  return wrapper.findAll('.echart-stub').map(el => el.attributes('data-title'))
}

describe('开口率报表图表分析', () => {
  beforeEach(() => {
    api.get.mockReset()
    api.get.mockResolvedValue({ data: reportData })
  })

  it('接触量大于0时默认渲染排行页签三张图', async () => {
    const wrapper = await mountPage()
    expect(chartTitles(wrapper)).toEqual(['班组开口率排行', '班级开口率排行', '员工开口率排行'])
  })

  it('切换到趋势页签渲染按日开口趋势和五大产品已开口趋势', async () => {
    const wrapper = await mountPage()
    wrapper.vm.$.setupState.chartSection = 'trend'
    await flushPromises()
    expect(chartTitles(wrapper)).toEqual(['按日开口趋势', '按日五大产品已开口量趋势'])
  })

  it('切换到产品页签渲染分产品开口量和占比饼图', async () => {
    const wrapper = await mountPage()
    wrapper.vm.$.setupState.chartSection = 'product'
    await flushPromises()
    expect(chartTitles(wrapper)).toEqual(['分产品开口量', '五大产品已开口占比'])
  })

  it('接触量为0时整个图表区域不渲染', async () => {
    api.get.mockResolvedValue({
      data: { ...reportData, stats: { ...reportData.stats, contact_count: 0 } }
    })
    const wrapper = await mountPage()
    expect(wrapper.findAll('.echart-stub')).toHaveLength(0)
  })
})
