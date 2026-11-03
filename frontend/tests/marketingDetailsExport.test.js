import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

vi.mock('../src/stores/user', () => {
  const get = vi.fn()
  const post = vi.fn()
  return {
    api: { get, post },
    useUserStore: vi.fn(() => ({ hasPermission: vi.fn(() => true) }))
  }
})

vi.mock('../src/stores/uiConfig', () => ({
  useUiConfigStore: vi.fn(() => ({ labels: { marketing_orders: '营销明细' }, loaded: true }))
}))

vi.mock('../src/utils/download', () => ({ downloadBlob: vi.fn() }))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), warning: vi.fn(), success: vi.fn() },
  ElMessageBox: { confirm: vi.fn() }
}))

import { api } from '../src/stores/user'
import { downloadBlob } from '../src/utils/download'
import MarketingDetails from '../src/views/MarketingDetails.vue'

const stubs = {
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button><slot /></button>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-date-picker': { template: '<input />' },
  'el-select': { template: '<div><slot /></div>' },
  'el-option': { template: '<div />' },
  'el-input': { template: '<input />' },
  'el-space': { template: '<div><slot /></div>' },
  'el-table': { template: '<table><slot /></table>' },
  'el-table-column': { template: '<col />' },
  'el-pagination': { template: '<div />' },
  'el-dialog': { template: '<div><slot /><slot name="footer" /></div>' },
  'el-upload': { template: '<div><slot /><slot name="tip" /></div>' },
  'el-icon': { template: '<i><slot /></i>' },
  'el-tag': { template: '<span><slot /></span>' }
}

const DEPT_A = '广西分公司>>省中心>>客户服务营销中心>>A部门'
const DEPT_B = '广西分公司>>省中心>>客户服务营销中心>>B部门'

function reportData() {
  return {
    items: [],
    total: 0,
    options: {
      team_options: [
        { dept: DEPT_A, dept_group: '一组', team: '一班1组' },
        { dept: DEPT_B, dept_group: '二组', team: '一班1组' }
      ],
      class_options: [
        { dept: DEPT_A, dept_group: '一组', class_name: '一班' },
        { dept: DEPT_B, dept_group: '二组', class_name: '一班' }
      ]
    }
  }
}

describe('营销明细导出', () => {
  beforeEach(() => {
    api.get.mockReset()
    api.post.mockReset()
    api.get.mockResolvedValue({ data: reportData() })
    downloadBlob.mockReset()
  })

  it('按当前筛选条件导出全部匹配记录', async () => {
    const wrapper = mount(MarketingDetails, { global: { stubs } })
    await flushPromises()
    const state = wrapper.vm.$.setupState
    state.searchForm.kf_id = 'A001'
    state.searchForm.data_type = 'xszb'
    state.range = ['2026-10-01', '2026-10-31']

    state.handleExport()

    expect(downloadBlob).toHaveBeenCalledWith(
      '/marketing/details/export',
      {
        kf_id: 'A001',
        data_type: 'xszb',
        start_date: '2026-10-01',
        end_date: '2026-10-31'
      },
      '营销明细.csv'
    )
  })

  it('班组与班级筛选按部门组合参数导出', async () => {
    const wrapper = mount(MarketingDetails, { global: { stubs } })
    await flushPromises()
    const state = wrapper.vm.$.setupState

    state.searchForm.team_key = `${DEPT_A}\u0001一班1组`
    await nextTick()
    state.handleExport()
    expect(downloadBlob).toHaveBeenLastCalledWith(
      '/marketing/details/export',
      { dept: DEPT_A, team: '一班1组' },
      '营销明细.csv'
    )

    state.searchForm.class_key = `${DEPT_B}\u0001一班`
    await flushPromises()
    await nextTick()
    expect(state.searchForm.team_key).toBe('')
    state.handleExport()
    expect(downloadBlob).toHaveBeenLastCalledWith(
      '/marketing/details/export',
      { dept: DEPT_B, class_name: '一班' },
      '营销明细.csv'
    )
  })
})
