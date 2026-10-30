import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

vi.mock('../src/stores/user', () => {
  const get = vi.fn()
  return {
    api: { get },
    useUserStore: vi.fn(() => ({ hasPermission: vi.fn(() => true) }))
  }
})

vi.mock('../src/stores/uiConfig', () => ({
  useUiConfigStore: vi.fn(() => ({ labels: { marketing_report: '营销统计' }, loaded: true }))
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn() }
}))

import { api } from '../src/stores/user'
import MarketingReport from '../src/views/MarketingReport.vue'
import { classKey, teamKey } from '../src/utils/teamIdentity'

const DEPT_A = '广西分公司>>省中心>>客户服务营销中心>>热线运营组>>A部门'
const DEPT_B = '广西分公司>>省中心>>客户服务营销中心>>热线运营组>>B部门'

const reportData = {
  stats: {},
  employees: [], teams: [], groups: [], products: [], days: [],
  options: {
    groups: [], orgs: [], products: [], sources: [],
    team_options: [
      { dept: DEPT_A, team: '一班1组' },
      { dept: DEPT_B, team: '一班1组' }
    ],
    class_options: [
      { dept: DEPT_A, class_name: '一班' },
      { dept: DEPT_B, class_name: '一班' }
    ]
  }
}

const stubs = {
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button><slot /></button>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-radio-group': { template: '<div><slot /></div>' },
  'el-radio': { template: '<label><slot /></label>' },
  'el-radio-button': { template: '<label><slot /></label>' },
  'el-date-picker': { template: '<input />' },
  'el-select': { template: '<div><slot /></div>' },
  'el-option': { template: '<div />' },
  'el-input': { template: '<input />' },
  'el-row': { template: '<div><slot /></div>' },
  'el-col': { template: '<div><slot /></div>' },
  'el-statistic': { template: '<div />' },
  'el-tabs': { template: '<div><slot /></div>' },
  'el-tab-pane': { template: '<div />' },
  'el-table': { template: '<table><slot /></table>' },
  'el-table-column': { template: '<col />' },
  Echart: { template: '<div />' }
}

async function mountPage() {
  const wrapper = mount(MarketingReport, { global: { stubs } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('营销统计班组/班级部门隔离', () => {
  beforeEach(() => {
    api.get.mockReset()
    api.get.mockResolvedValue({ data: reportData })
  })

  it('班级与班组筛选互斥，并按选中项发送部门参数', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState

    state.searchForm.class_key = classKey(DEPT_A, '一班')
    await nextTick()
    expect(state.searchForm.team_key).toBe('')
    expect(state.buildParams()).toMatchObject({ dept: DEPT_A, class_name: '一班' })

    state.searchForm.team_key = teamKey(DEPT_B, '一班1组')
    await nextTick()
    expect(state.searchForm.class_key).toBe('')
    expect(state.buildParams()).toMatchObject({ dept: DEPT_B, team: '一班1组' })
  })

  it('图表点击同名班组时使用组合 key 并清空班级', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState
    state.searchForm.class_key = classKey(DEPT_A, '一班')
    await nextTick()

    state.handleTeamChartClick({ data: { team_key: teamKey(DEPT_B, '一班1组') } })
    await flushPromises()

    expect(state.searchForm.team_key).toBe(teamKey(DEPT_B, '一班1组'))
    expect(state.searchForm.class_key).toBe('')
  })
})
