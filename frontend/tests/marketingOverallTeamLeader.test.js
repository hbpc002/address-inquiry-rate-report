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

vi.mock('../src/stores/uiConfig', () => ({
  useUiConfigStore: vi.fn(() => ({
    labels: {
      marketing_overall_report: '总体营销'
    },
    loaded: true
  }))
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() }
}))

import { api } from '../src/stores/user'
import MarketingOverallReport from '../src/views/MarketingOverallReport.vue'

const reportData = {
  stats: {
    start_date: '2026-10-01',
    end_date: '2026-10-31',
    grand_total: 3,
    unclassified_rows: 0,
    unclassified_business_rows: 0
  },
  columns: [{ key: 'overlay', label: '叠加包' }],
  rows: [],
  total_row: { counts: { overlay: 0 }, total: 0 },
  key_product_columns: [{ key: 'key_product_0', label: '业务A' }],
  key_product_rows: [
    {
      work_group: '热线',
      team: '热线一组',
      leader: '王组长、赵组长',
      rowspan: 3,
      counts: { key_product_0: 2 },
      total: 2,
      is_subtotal: false
    },
    {
      work_group: '热线',
      team: '未分班组',
      leader: '',
      rowspan: 0,
      counts: { key_product_0: 1 },
      total: 1,
      is_subtotal: false
    },
    {
      work_group: '热线',
      team: '小计',
      rowspan: 0,
      counts: { key_product_0: 3 },
      total: 3,
      is_subtotal: true
    }
  ],
  key_product_total_row: { counts: { key_product_0: 3 }, total: 3 },
  data_ranges: { database: {}, query: {} }
}

const stubs = {
  'el-card': { template: '<div class="el-card-stub"><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button class="el-button-stub"><slot /></button>' },
  'el-form': { template: '<form class="el-form-stub"><slot /></form>' },
  'el-form-item': { template: '<div class="el-form-item-stub"><slot /></div>' },
  'el-radio-group': { template: '<div class="el-radio-group-stub"><slot /></div>' },
  'el-radio': { template: '<label class="el-radio-stub"><slot /></label>' },
  'el-radio-button': { template: '<label class="el-radio-button-stub"><slot /></label>' },
  'el-date-picker': { template: '<input class="el-date-picker-stub" />' },
  'el-alert': { template: '<div class="el-alert-stub" />' }
}

async function mountPage() {
  const wrapper = mount(MarketingOverallReport, {
    global: { stubs }
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('总体营销重点业务产品班组组长显示', () => {
  beforeEach(() => {
    api.get.mockReset()
    api.get.mockResolvedValue({ data: reportData })
  })

  it('班组名称后显示组长，多个组长用顿号拼接', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('.key-product-table tbody tr')

    expect(rows[0].find('.team-col').text()).toBe('热线一组（王组长、赵组长）')
    expect(rows[1].find('.team-col').text()).toBe('未分班组')
    expect(rows[2].find('.team-col').text()).toBe('小计')
  })
})
