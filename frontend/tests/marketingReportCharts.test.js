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
      marketing_report: '营销统计'
    },
    loaded: true
  }))
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn() }
}))

import { api } from '../src/stores/user'
import MarketingReport from '../src/views/MarketingReport.vue'

const reportData = {
  stats: {
    total: 100,
    order_count: 60,
    inbound: 70,
    outbound: 20,
    overlay: 70,
    package_change: 20,
    overlay_day: 10,
    overlay_month: 30,
    overlay_long: 20,
    overlay_undefined: 10,
    people_count: 2
  },
  employees: [
    {
      kf_id: 'KF001', name: '张三', team: '热线一组', dept: '客服部', group_name: '线上直办-热线',
      total: 40, order_count: 20, inbound: 30, outbound: 10, overlay: 28, package_change: 8,
      overlay_day: 4, overlay_month: 12, overlay_long: 8, overlay_undefined: 4
    },
    {
      kf_id: 'KF002', name: '李四', team: '热线二组', dept: '客服部', group_name: '线上直办-热线',
      total: 60, order_count: 40, inbound: 40, outbound: 10, overlay: 42, package_change: 12,
      overlay_day: 6, overlay_month: 18, overlay_long: 12, overlay_undefined: 6
    }
  ],
  teams: [
    {
      team: '热线一组', leader: '王组长', people: 1, total: 40, order_count: 20,
      inbound: 30, outbound: 10, overlay: 28, package_change: 8,
      overlay_day: 4, overlay_month: 12, overlay_long: 8, overlay_undefined: 4
    },
    {
      team: '热线二组', leader: '赵组长', people: 1, total: 60, order_count: 40,
      inbound: 40, outbound: 10, overlay: 42, package_change: 12,
      overlay_day: 6, overlay_month: 18, overlay_long: 12, overlay_undefined: 6
    }
  ],
  groups: [
    { group_name: '线上直办-热线', people: 2, total: 100, order_count: 60, inbound: 70, outbound: 20, overlay: 70, package_change: 20, overlay_day: 10, overlay_month: 30, overlay_long: 20, overlay_undefined: 10 }
  ],
  products: [
    { product_id: 'P1', product_name: '产品A', total: 70, order_count: 40, inbound: 50, outbound: 15, overlay: 70, package_change: 0, overlay_day: 10, overlay_month: 30, overlay_long: 20, overlay_undefined: 10 },
    { product_id: 'P2', product_name: '产品B', total: 30, order_count: 20, inbound: 20, outbound: 5, overlay: 0, package_change: 20, overlay_day: 0, overlay_month: 0, overlay_long: 0, overlay_undefined: 0 }
  ],
  days: [
    { date: '2026-10-01', total: 40, order_count: 20, inbound: 30, outbound: 10, overlay: 28, package_change: 8, overlay_day: 4, overlay_month: 12, overlay_long: 8, overlay_undefined: 4 },
    { date: '2026-10-02', total: 60, order_count: 40, inbound: 40, outbound: 10, overlay: 42, package_change: 12, overlay_day: 6, overlay_month: 18, overlay_long: 12, overlay_undefined: 6 }
  ],
  options: { groups: [], teams: [], orgs: [], products: [], sources: [] }
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
  'el-select': { template: '<div class="el-select-stub"><slot /></div>' },
  'el-option': { template: '<div class="el-option-stub" />' },
  'el-input': { template: '<input class="el-input-stub" />' },
  'el-row': { template: '<div class="el-row-stub"><slot /></div>' },
  'el-col': { template: '<div class="el-col-stub"><slot /></div>' },
  'el-statistic': { template: '<div class="el-statistic-stub" />' },
  'el-tabs': {
    emits: ['update:modelValue', 'tab-change'],
    template: '<div class="el-tabs-stub"><slot /></div>'
  },
  'el-tab-pane': { template: '<div class="el-tab-pane-stub" />' },
  'el-table': { template: '<table class="el-table-stub"><slot /></table>' },
  'el-table-column': { template: '<col class="el-table-column-stub" />' },
  Echart: {
    props: ['options', 'height'],
    template: '<div class="echart-stub" :data-height="height" :data-title="options && options.title ? options.title.text : \'\'"></div>'
  }
}

async function mountPage() {
  const wrapper = mount(MarketingReport, {
    global: { stubs }
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

async function switchSection(wrapper, section) {
  wrapper.vm.$.setupState.chartSection = section
  await flushPromises()
}

describe('营销统计图表区域', () => {
  beforeEach(() => {
    api.get.mockReset()
    api.get.mockResolvedValue({ data: reportData })
  })

  it('仅保留班组、趋势、辅助维度三个图表页签，默认展示班组分析', async () => {
    const wrapper = await mountPage()
    const tabLabels = wrapper.findAll('.el-radio-button-stub').map(tab => tab.text())
    expect(tabLabels).toEqual(['班组分析', '趋势分析', '辅助维度'])
    expect(wrapper.vm.$.setupState.chartSection).toBe('team')

    const titles = wrapper.findAll('.echart-stub').map(chart => chart.attributes('data-title'))
    expect(titles).toHaveLength(10)
    expect(titles).toContain('班组产品办理量排行')
    expect(titles).toContain('班组人均办理量排行')
    expect(titles).toContain('班组人均订单数排行')
    expect(titles).toContain('班组订单覆盖率排行')
    expect(titles).toContain('班组多指标雷达')
    expect(titles).toContain('班组人均效率分布')
    expect(titles).toContain('班组办理量帕累托图')
    expect(titles.join(' ')).not.toContain('部门')
    expect(titles.join(' ')).not.toContain('组织')
  })

  it('班组分析存在正常班组时过滤未匹配班组', async () => {
    api.get.mockResolvedValue({
      data: {
        ...reportData,
        teams: [
          ...reportData.teams,
          {
            team: '未匹配班组', leader: '', people: 1, total: 10, order_count: 5,
            inbound: 8, outbound: 2, overlay: 7, package_change: 2,
            overlay_day: 1, overlay_month: 3, overlay_long: 2, overlay_undefined: 1
          }
        ]
      }
    })
    const wrapper = await mountPage()
    const teamLabels = wrapper.vm.$.setupState.teamItems.map(item => item.displayName)
    expect(teamLabels).toEqual(['热线一组', '热线二组'])
  })

  it('趋势分析和辅助维度图表数量与标题正确', async () => {
    const wrapper = await mountPage()
    await switchSection(wrapper, 'trend')
    const trendTitles = wrapper.findAll('.echart-stub').map(chart => chart.attributes('data-title'))
    expect(trendTitles).toEqual([
      '每日办理趋势',
      '每日业务结构',
      '每日来话/去话结构',
      '每日叠加包有效期结构',
      '每日订单覆盖率'
    ])

    await switchSection(wrapper, 'auxiliary')
    const auxTitles = wrapper.findAll('.echart-stub').map(chart => chart.attributes('data-title'))
    expect(auxTitles).toEqual([
      '产品办理量排行',
      '行分类办理量排行',
      '产品业务结构',
      '产品来话/去话结构',
      '行分类业务结构',
      '行分类来话/去话结构'
    ])
  })
})
