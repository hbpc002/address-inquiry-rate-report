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
  createPieOptions: vi.fn(() => ({})),
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
    template: '<div class="echart-stub" :data-height="height" @click="$emit(\'click\', $event)"></div>'
  }
}))

import { api } from '../src/stores/user'
import BroadbandReport from '../src/views/BroadbandReport.vue'

const items = [
  { emp_no: 'KF770001', name: '张三', team: '云网一组', intention_count: 3, recommend: 3, completed: 2, success_rate: 0.6667 },
  { emp_no: 'KF770002', name: '李四', team: '云网一组', intention_count: 2, recommend: 2, completed: 1, success_rate: 0.5 },
]

const statsPayload = {
  stats: {
    total_people: 2,
    total_recommend: 5,
    total_completed: 3,
    avg_success_rate: 0.6,
    teams: ['云网一组'],
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
  'el-option': { template: '<div class="el-option-stub" />' },
  'el-pagination': { template: '<div class="el-pagination-stub" />' },
  'el-radio': { props: ['value'], template: '<label class="el-radio-stub"><slot /></label>' },
  'el-radio-group': { template: '<div class="el-radio-group-stub"><slot /></div>' },
  'el-row': { template: '<div class="el-row-stub"><slot /></div>' },
  'el-select': { template: '<div class="el-select-stub"><slot /></div>' },
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
    api.get.mockImplementation((url) => {
      if (url === '/broadband/report') return Promise.resolve({ data: statsPayload })
      return Promise.resolve({ data: [] })
    })
  })

  function scatterStub(wrapper) {
    return wrapper.findAll('.echart-stub')[0]
  }

  it('初始：搜索栏可见，散点图高度为 480px', async () => {
    const wrapper = await mountPage()
    const forms = wrapper.findAll('.el-form-stub')
    expect(forms).toHaveLength(2)
    forms.forEach((form) => expect(isHidden(form)).toBe(false))
    expect(scatterStub(wrapper).attributes('data-height')).toBe('480px')
  })

  function isHidden(form) {
    return (form.attributes('style') || '').includes('display: none')
  }

  it('点击散点图：隐藏搜索栏且高度接近整屏，再点还原', async () => {
    const wrapper = await mountPage()
    await scatterStub(wrapper).trigger('click', { componentType: 'series' })
    await flushPromises()

    wrapper.findAll('.el-form-stub').forEach((form) => expect(isHidden(form)).toBe(true))
    expect(scatterStub(wrapper).attributes('data-height')).toBe('calc(100vh - 240px)')

    await scatterStub(wrapper).trigger('click', { componentType: 'series' })
    await flushPromises()

    wrapper.findAll('.el-form-stub').forEach((form) => expect(isHidden(form)).toBe(false))
    expect(scatterStub(wrapper).attributes('data-height')).toBe('480px')
  })

  it('点击图例不触发放大/还原', async () => {
    const wrapper = await mountPage()
    await scatterStub(wrapper).trigger('click', { componentType: 'legend', name: '云网一组' })
    await flushPromises()

    wrapper.findAll('.el-form-stub').forEach((form) => expect(isHidden(form)).toBe(false))
    expect(scatterStub(wrapper).attributes('data-height')).toBe('480px')
  })
})