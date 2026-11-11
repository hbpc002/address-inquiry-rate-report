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
      dept: '广西分公司>>A部门',
      dept_group: '第一部门组',
      team: '热线一组',
      leader: '王组长、赵组长',
      rowspan: 4,
      counts: { key_product_0: 2 },
      total: 2,
      is_subtotal: false
    },
    {
      work_group: '热线',
      dept: '广西分公司>>B部门',
      dept_group: '第二部门组',
      team: '热线一组',
      leader: '李组长',
      rowspan: 0,
      counts: { key_product_0: 1 },
      total: 1,
      is_subtotal: false
    },
    {
      work_group: '热线',
      dept: '',
      dept_group: '',
      team: '未分班组',
      leader: '',
      rowspan: 0,
      counts: { key_product_0: 1 },
      total: 1,
      is_subtotal: false
    },
    {
      work_group: '热线',
      dept: '',
      dept_group: '',
      team: '小计',
      rowspan: 0,
      counts: { key_product_0: 4 },
      total: 4,
      is_subtotal: true
    }
  ],
  key_product_total_row: { counts: { key_product_0: 4 }, total: 4 },
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
  'el-alert': { props: ['title'], template: '<div class="el-alert-stub">{{ title }}</div>' }
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

  it('重名班组只显示班组和组长，不显示部门组后缀', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('.key-product-table tbody tr')

    expect(rows[0].find('.team-col').text()).toBe('热线一组（王组长、赵组长）')
    expect(rows[1].find('.team-col').text()).toBe('热线一组（李组长）')
    expect(rows[2].find('.team-col').text()).toBe('未分班组')
    expect(rows[3].find('.team-col').text()).toBe('小计')
  })

  it('显示宽带营销数据范围和未分类宽带订单提示', async () => {
    api.get.mockResolvedValue({
      data: {
        ...reportData,
        stats: { ...reportData.stats, unclassified_broadband_rows: 2, unclassified_broadband_no_org_rows: 1 },
        data_ranges: {
          database: {
            xszb: { start_date: '2026-10-01', end_date: '2026-10-31' },
            fwgd: { start_date: '2026-10-01', end_date: '2026-10-31' },
            broadband: { start_date: '2026-10-03', end_date: '2026-10-28' }
          },
          query: {
            xszb: { start_date: '2026-10-01', end_date: '2026-10-31' },
            fwgd: { start_date: '2026-10-01', end_date: '2026-10-31' },
            broadband: { start_date: '2026-10-03', end_date: '2026-10-28' }
          }
        }
      }
    })
    const wrapper = await mountPage()
    const ranges = wrapper.findAll('.query-range-item')

    expect(ranges[2].text()).toContain('宽带营销数据')
    expect(ranges[2].text()).toContain('2026-10-03 ~ 2026-10-28')
    expect(wrapper.text()).toContain('2 条宽带订单未匹配行分类规则')
    expect(wrapper.text()).toContain('其中 1 条工号未匹配组织机构')
  })
})
