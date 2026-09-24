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
      project_name: '客户服务中心运营管理平台',
      dashboard: '工效仪表盘',
      checkin_report: '排班调度',
      workload_report: '团队管理',
      broadband_report: '宽带营销画像',
      reports: '考勤报表',
      menu_data: '数据管理',
      schedules: '排班管理',
      employees: '员工管理',
      checkins: '签到记录',
      training_records: '培训记录',
      workload: '工作量详单',
      broadband_orders: '无缝订单',
      menu_system: '系统设置',
      system: '系统管理',
      users: '用户管理',
      roles: '角色管理',
      work_hour_settings: '工时预警设置',
      salary_config: '绩效配置',
      field_annotations: '字段批注',
      agent: '哟你通通',
    },
    loaded: true,
  }))
}))

vi.mock('../src/utils/echarts', () => ({
  createPieOptions: vi.fn(() => ({ type: 'pie' })),
  createBarOptions: vi.fn(() => ({ type: 'bar', xAxis: {}, grid: {} })),
  CHART_COLORS: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
}))

vi.mock('../src/utils/download', () => ({
  downloadBlob: vi.fn()
}))

vi.mock('../src/components/Echart.vue', () => ({
  default: {
    name: 'Echart',
    props: ['options', 'height'],
    emits: ['click'],
    template: '<div class="echart-stub" :data-height="height" :data-title-show="String(options.title == null ? true : options.title.show)" :data-x="String(options.xAxis == null ? \'\' : options.xAxis.name)" :data-y="String(options.yAxis == null ? \'\' : options.yAxis.name)" @click="$emit(\'click\', $event)"></div>'
  }
}))

import { api } from '../src/stores/user'
import { createPieOptions, createBarOptions } from '../src/utils/echarts'
import BroadbandReport from '../src/views/BroadbandReport.vue'

const items = [
  { emp_no: 'KF770001', name: '张三', team: '云网一组', intention_count: 3, recommend: 3, completed: 2, success_rate: 0.6667 },
  { emp_no: 'KF770002', name: '李四', team: '云网一组', intention_count: 2, recommend: 2, completed: 1, success_rate: 0.5 },
  { emp_no: 'KF770003', name: '王五', team: '云网二组', intention_count: 3, recommend: 3, completed: 3, success_rate: 1 },
]

const statsPayload = {
  stats: {
    total_people: 3,
    total_recommend: 8,
    total_completed: 6,
    avg_success_rate: 0.7,
    teams: ['云网一组', '云网二组'],
    classes: [],
    cities: []
  },
  items
}

const stubs = {
  'el-button': { template: '<button class="el-button-stub"><slot /></button>' },
  'el-card': { template: '<div class="el-card-stub"><slot name="header" /><slot /></div>' },
  'el-col': {
    props: ['span'],
    template: '<div class="el-col-stub" :data-span="span != null ? String(span) : \'\'"><slot /></div>'
  },
  'el-date-picker': { template: '<input type="text" class="el-date-picker-stub" />' },
  'el-form': { template: '<form class="el-form-stub"><slot /></form>' },
  'el-form-item': { props: ['label'], template: '<div class="el-form-item-stub"><span class="el-form-item-label">{{ label }}</span><slot /></div>' },
  'el-input': { template: '<input type="text" class="el-input-stub" />' },
  'el-option': { props: ['value', 'label'], template: '<option class="el-option-stub" :value="value">{{ label }}</option>' },
  'el-pagination': { template: '<div class="el-pagination-stub" />' },
  'el-radio': { props: ['value'], template: '<label class="el-radio-stub"><slot /></label>' },
  'el-radio-group': { template: '<div class="el-radio-group-stub"><slot /></div>' },
  'el-row': { template: '<div class="el-row-stub"><slot /></div>' },
  'el-select': {
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: '<select class="el-select-stub" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><slot /></select>'
  },
  'el-statistic': {
    props: ['title', 'value', 'precision'],
    template: '<div class="el-statistic-stub" :data-title="title"><span>{{ title }}</span><span>{{ value }}</span><slot name="suffix" /></div>'
  },
  'el-table': { template: '<table class="el-table-stub"><slot /></table>' },
  'el-table-column': { template: '<col class="el-table-column-stub" />' }
}

async function mountPage() {
  const wrapper = mount(BroadbandReport, {
    global: { stubs }
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('宽带画像散点图点击放大/还原视图', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    createPieOptions.mockClear()
    createBarOptions.mockClear()
    api.get.mockClear()
    api.get.mockImplementation((url) => {
      if (url === '/broadband/report') return Promise.resolve({ data: statsPayload })
      return Promise.resolve({ data: [] })
    })
  })

  function scatterStub(wrapper) {
    return wrapper.findAll('.echart-stub')[0]
  }

  function pieStub(wrapper) {
    return wrapper.findAll('.echart-stub')[1]
  }

  function isHidden(el) {
    return (el.attributes('style') || '').includes('display: none')
  }

  it('初始：搜索栏与指标栏可见，散点图高 480px、自带标题显示、轴选择器可见', async () => {
    const wrapper = await mountPage()
    const forms = wrapper.findAll('.el-form-stub')
    expect(forms).toHaveLength(2)
    forms.forEach((form) => expect(isHidden(form)).toBe(false))
    expect(isHidden(wrapper.find('.stats-row'))).toBe(false)
    expect(scatterStub(wrapper).attributes('data-height')).toBe('480px')
    expect(scatterStub(wrapper).attributes('data-title-show')).toBe('true')
    expect(scatterStub(wrapper).attributes('data-x')).toBe('推荐量')
    expect(scatterStub(wrapper).attributes('data-y')).toBe('成功率(%)')
    expect(wrapper.findAll('.scatter-axis-select')).toHaveLength(2)
    expect(wrapper.find('.scatter-toolbar').exists()).toBe(true)
    expect(wrapper.findAll('.el-card-stub')).toHaveLength(3)
    expect(wrapper.find('.stats-overlay').exists()).toBe(false)
  })

  it('点击散点图：搜索栏/指标栏隐藏，指标叠加在图上、高度整屏、只留一层卡片，再点还原', async () => {
    const wrapper = await mountPage()
    await scatterStub(wrapper).trigger('click', { componentType: 'series' })
    await flushPromises()

    wrapper.findAll('.el-form-stub').forEach((form) => expect(isHidden(form)).toBe(true))
    expect(isHidden(wrapper.find('.stats-row'))).toBe(true)
    expect(wrapper.find('.stats-overlay').exists()).toBe(true)
    expect(wrapper.find('.stats-overlay').findAll('.el-statistic-stub')).toHaveLength(4)
    expect(scatterStub(wrapper).attributes('data-height')).toBe('calc(100vh - 240px)')
    expect(scatterStub(wrapper).attributes('data-title-show')).toBe('false')
    expect(wrapper.find('.scatter-toolbar').exists()).toBe(false)
    expect(wrapper.findAll('.el-card-stub')).toHaveLength(2)

    await scatterStub(wrapper).trigger('click', { componentType: 'series' })
    await flushPromises()

    wrapper.findAll('.el-form-stub').forEach((form) => expect(isHidden(form)).toBe(false))
    expect(isHidden(wrapper.find('.stats-row'))).toBe(false)
    expect(wrapper.find('.stats-overlay').exists()).toBe(false)
    expect(scatterStub(wrapper).attributes('data-height')).toBe('480px')
    expect(scatterStub(wrapper).attributes('data-title-show')).toBe('true')
    expect(wrapper.findAll('.el-card-stub')).toHaveLength(3)
  })

  it('点击图例不触发放大/还原', async () => {
    const wrapper = await mountPage()
    await scatterStub(wrapper).trigger('click', { componentType: 'legend', name: '云网一组' })
    await flushPromises()

    wrapper.findAll('.el-form-stub').forEach((form) => expect(isHidden(form)).toBe(false))
    expect(isHidden(wrapper.find('.stats-row'))).toBe(false)
    expect(wrapper.find('.stats-overlay').exists()).toBe(false)
    expect(scatterStub(wrapper).attributes('data-height')).toBe('480px')
  })
})

describe('宽带画像饼图→组员柱形图（参照团队管理）', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    createPieOptions.mockClear()
    createBarOptions.mockClear()
    api.get.mockClear()
    api.get.mockImplementation((url) => {
      if (url === '/broadband/report') return Promise.resolve({ data: statsPayload })
      return Promise.resolve({ data: [] })
    })
  })

  function scatterStub(wrapper) {
    return wrapper.findAll('.echart-stub')[0]
  }

  function pieStub(wrapper) {
    return wrapper.findAll('.echart-stub')[1]
  }

  it('初始：图表区域展示班组饼图，不触发柱形图', async () => {
    const wrapper = await mountPage()
    expect(createPieOptions).toHaveBeenCalledTimes(1)
    expect(createPieOptions.mock.calls[0][0].map(d => d.name)).toEqual(['云网一组', '云网二组'])
    expect(createBarOptions).not.toHaveBeenCalled()
    expect(pieStub(wrapper).attributes('data-height')).toBe('360px')
    expect(scatterStub(wrapper).attributes('data-height')).toBe('480px')
  })

  it('点击班组：切换为组员推荐量柱形图，且不再重新请求', async () => {
    const wrapper = await mountPage()
    await pieStub(wrapper).trigger('click', { componentType: 'series', name: '云网一组' })
    await flushPromises()

    expect(createBarOptions).toHaveBeenCalledTimes(1)
    const [names, values, title] = createBarOptions.mock.calls[0]
    expect(names).toEqual(['张三', '李四'])
    expect(values).toEqual([3, 2])
    expect(title).toBe('云网一组 成员推荐量')
    expect(createPieOptions).toHaveBeenCalledTimes(1)
    expect(api.get.mock.calls.filter(c => c[0] === '/broadband/report')).toHaveLength(1)
  })

  it('再次点击柱形图：回到班组饼图', async () => {
    const wrapper = await mountPage()
    await pieStub(wrapper).trigger('click', { componentType: 'series', name: '云网一组' })
    await flushPromises()
    await pieStub(wrapper).trigger('click', { componentType: 'series', name: '李四' })
    await flushPromises()

    expect(createPieOptions).toHaveBeenCalledTimes(2)
    expect(createBarOptions).toHaveBeenCalledTimes(1)
    expect(api.get.mock.calls.filter(c => c[0] === '/broadband/report')).toHaveLength(1)
  })

  it('点击空白（无 name）不触发切换', async () => {
    const wrapper = await mountPage()
    await pieStub(wrapper).trigger('click', { componentType: 'series' })
    await flushPromises()

    expect(createBarOptions).not.toHaveBeenCalled()
    expect(createPieOptions).toHaveBeenCalledTimes(1)
  })
})

describe('宽带画像散点图自定义轴与持久化', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    api.get.mockClear()
    api.get.mockImplementation((url) => {
      if (url === '/broadband/report') return Promise.resolve({ data: statsPayload })
      return Promise.resolve({ data: [] })
    })
  })

  function scatterStub(wrapper) {
    return wrapper.findAll('.echart-stub')[0]
  }

  function axisSelects(wrapper) {
    return wrapper.findAll('.scatter-axis-select')
  }

  async function pickAxis(wrapper, index, value) {
    const select = axisSelects(wrapper)[index]
    select.element.value = value
    await select.trigger('change')
    await flushPromises()
  }

  it('切换 X 轴为成功推荐：轴名与本地缓存同步更新', async () => {
    const wrapper = await mountPage()
    await pickAxis(wrapper, 0, 'completed')

    expect(scatterStub(wrapper).attributes('data-x')).toBe('成功推荐')
    expect(scatterStub(wrapper).attributes('data-y')).toBe('成功率(%)')
    expect(JSON.parse(localStorage.getItem('broadband-report-scatter-axes'))).toEqual({
      x: 'completed',
      y: 'success_rate'
    })
  })

  it('切换 Y 轴为成功推荐：仅 Y 轴名更新，X 不变', async () => {
    const wrapper = await mountPage()
    await pickAxis(wrapper, 1, 'completed')

    expect(scatterStub(wrapper).attributes('data-x')).toBe('推荐量')
    expect(scatterStub(wrapper).attributes('data-y')).toBe('成功推荐')
  })

  it('把 X 选成与 Y 相同维度时自动交换两轴', async () => {
    const wrapper = await mountPage()
    await pickAxis(wrapper, 0, 'success_rate')

    expect(scatterStub(wrapper).attributes('data-x')).toBe('成功率(%)')
    expect(scatterStub(wrapper).attributes('data-y')).toBe('推荐量')
  })

  it('重新进入页面恢复持久化的轴选择', async () => {
    localStorage.setItem('broadband-report-scatter-axes', JSON.stringify({ x: 'completed', y: 'recommend' }))
    const wrapper = await mountPage()

    expect(scatterStub(wrapper).attributes('data-x')).toBe('成功推荐')
    expect(scatterStub(wrapper).attributes('data-y')).toBe('推荐量')
  })

  it('本地缓存为非法 JSON 或无效字段时回退到默认 推荐量×成功率', async () => {
    localStorage.setItem('broadband-report-scatter-axes', '{bad json')
    const wrapperA = await mountPage()
    expect(scatterStub(wrapperA).attributes('data-x')).toBe('推荐量')
    expect(scatterStub(wrapperA).attributes('data-y')).toBe('成功率(%)')

    localStorage.setItem('broadband-report-scatter-axes', JSON.stringify({ x: 'same', y: 'same' }))
    const wrapperB = await mountPage()
    expect(scatterStub(wrapperB).attributes('data-x')).toBe('推荐量')
    expect(scatterStub(wrapperB).attributes('data-y')).toBe('成功率(%)')
  })
})