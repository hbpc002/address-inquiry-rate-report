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

vi.mock('../src/utils/download', () => ({
  downloadBlob: vi.fn()
}))

import { api } from '../src/stores/user'
import { downloadBlob } from '../src/utils/download'
import BroadbandCompare from '../src/views/BroadbandCompare.vue'

const payload = {
  stats: {
    total_people: 2,
    total_recommend: 6,
    total_completed_by_order: 4,
    total_completed_by_finish: 3,
    total_diff: -1,
    avg_success_rate_by_order: 0.6667,
    avg_success_rate_by_finish: 0.5,
    total_points_by_order: 52,
    total_points_by_finish: 42,
    teams: ['云网一组', '云网二组'],
    classes: ['云网'],
    cities: ['南宁', '柳州']
  },
  items: [
    {
      emp_no: 'KF770001', name: '张三', team: '云网一组',
      recommend: 4, completed_by_order: 3, completed_by_finish: 3, diff: 0,
      success_rate_by_order: 0.75, success_rate_by_finish: 0.75,
      points_by_order: 38, points_by_finish: 38
    },
    {
      emp_no: 'KF770002', name: '李四', team: '云网二组',
      recommend: 2, completed_by_order: 1, completed_by_finish: 0, diff: -1,
      success_rate_by_order: 0.5, success_rate_by_finish: 0,
      points_by_order: 14, points_by_finish: 4
    }
  ]
}

const stubs = {
  'el-alert': { props: ['title'], template: '<div class="el-alert-stub">{{ title }}</div>' },
  'el-button': { template: '<button class="el-button-stub"><slot /></button>' },
  'el-card': { template: '<div class="el-card-stub"><slot name="header" /><slot /></div>' },
  'el-date-picker': { template: '<input type="text" class="el-date-picker-stub" />' },
  'el-form': { template: '<form class="el-form-stub"><slot /></form>' },
  'el-form-item': { props: ['label'], template: '<div class="el-form-item-stub"><span>{{ label }}</span><slot /></div>' },
  'el-input': { template: '<input type="text" class="el-input-stub" />' },
  'el-option': { props: ['value', 'label'], template: '<option :value="value">{{ label }}</option>' },
  'el-radio': { props: ['value'], template: '<label class="el-radio-stub"><slot /></label>' },
  'el-radio-group': { template: '<div class="el-radio-group-stub"><slot /></div>' },
  'el-row': { template: '<div class="el-row-stub"><slot /></div>' },
  'el-select': { template: '<select class="el-select-stub"><slot /></select>' },
  'el-statistic': {
    props: ['title', 'value', 'precision'],
    template: '<div class="el-statistic-stub" :data-title="title">{{ title }}:{{ value }}</div>'
  },
  'el-table': { template: '<table class="el-table-stub"><slot /></table>' },
  'el-table-column': {
    props: ['prop', 'label'],
    template: '<col class="el-table-column-stub" :data-prop="prop != null ? String(prop) : \'\'" :data-label="label != null ? String(label) : \'\'" />'
  }
}

async function mountPage() {
  const wrapper = mount(BroadbandCompare, {
    global: { stubs }
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('宽带下单/竣工口径对比', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    api.get.mockClear()
    downloadBlob.mockClear()
    api.get.mockResolvedValue({ data: payload })
  })

  it('加载对比数据并展示两种口径指标', async () => {
    const wrapper = await mountPage()

    expect(api.get).toHaveBeenCalledWith('/broadband/report/compare', expect.any(Object))
    expect(wrapper.text()).toContain('下单/竣工口径对比')
    expect(wrapper.text()).toContain('跨期订单')

    const stats = wrapper.findAll('.el-statistic-stub')
    const byTitle = Object.fromEntries(stats.map(s => [s.attributes('data-title'), s.text()]))
    expect(byTitle['推荐量(下单)']).toContain('6')
    expect(byTitle['成功推荐(下单)']).toContain('4')
    expect(byTitle['成功推荐(竣工)']).toContain('3')
    expect(byTitle['口径差异']).toContain('-1')
    expect(byTitle['竣工口径成功率(%)']).toContain('50')

    const props = wrapper.findAll('.el-table-column-stub').map(c => c.attributes('data-prop'))
    expect(props).toContain('recommend')
    expect(props).toContain('completed_by_order')
    expect(props).toContain('completed_by_finish')
    expect(props).toContain('points_by_finish')
  })

  it('导出时携带当前筛选条件', async () => {
    const wrapper = await mountPage()
    const exportButton = wrapper.findAll('.el-button-stub').find(b => b.text() === '导出')

    expect(exportButton).toBeTruthy()
    await exportButton.trigger('click')

    expect(downloadBlob).toHaveBeenCalledWith(
      '/broadband/report/compare/export',
      expect.objectContaining({ year_month: expect.any(String) }),
      'broadband_compare.csv'
    )
  })
})
