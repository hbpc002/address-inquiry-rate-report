import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('../src/stores/user', () => {
  const get = vi.fn()
  const put = vi.fn()
  return {
    api: { get, put },
    useUserStore: vi.fn(() => ({ hasPermission: vi.fn(() => true) }))
  }
})

vi.mock('../src/stores/uiConfig', () => ({
  useUiConfigStore: vi.fn(() => ({
    labels: { marketing_settings: '营销设置' },
    loaded: true
  }))
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() }
}))

import { api } from '../src/stores/user'
import MarketingSettings from '../src/views/MarketingSettings.vue'

const overallRules = [
  {
    id: 'online-org',
    row_label: '线上直办-热线',
    field: 'org_name',
    match_type: 'contains',
    pattern: '热线运营组',
    priority: 1,
    enabled: true
  },
  {
    id: 'work-org',
    row_label: '营销工单-区域',
    field: 'org_name',
    match_type: 'contains',
    pattern: '区域组',
    priority: 2,
    enabled: true
  },
  {
    id: 'work-tenant',
    row_label: '营销工单-工单',
    field: 'tenant',
    match_type: 'contains',
    pattern: '南方二中心',
    priority: 3,
    enabled: true
  },
  {
    id: 'downgrade',
    row_label: '降套维系',
    field: 'service_type',
    match_type: 'equals',
    pattern: '降套',
    priority: 4,
    enabled: true
  }
]

const broadbandRules = {
  org_rules: [
    {
      id: 'bb-org',
      row_label: '营销工单-维系',
      field: 'org_name',
      match_type: 'contains',
      pattern: '维系',
      priority: 1,
      enabled: true
    }
  ],
  emp_rules: [
    {
      id: 'bb-emp',
      row_label: '营销工单-工单',
      match_type: 'equals',
      pattern: '--',
      priority: 2,
      enabled: true
    }
  ],
  inherited_org_rules: [
    {
      id: 'online-org',
      source: '线上直办规则',
      source_row_label: '线上直办-热线',
      row_label: '营销工单-热线',
      match_type: 'contains',
      pattern: '热线运营组',
      priority: 1,
      enabled: true
    }
  ]
}

const stubs = {
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button><slot /></button>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-alert': { template: '<div />' },
  'el-tabs': { template: '<div><slot /></div>' },
  'el-tab-pane': { template: '<div><slot /></div>' },
  'el-table': { template: '<table><slot /></table>' },
  'el-table-column': { template: '<col />' },
  'el-select': { template: '<div><slot /></div>' },
  'el-option': { template: '<div />' },
  'el-input': { template: '<input />' },
  'el-input-number': { template: '<input />' },
  'el-switch': { template: '<div />' },
  'el-tag': { template: '<span><slot /></span>' },
  'el-divider': { template: '<div><slot /></div>' }
}

async function mountPage() {
  const wrapper = mount(MarketingSettings, { global: { stubs } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.get.mockImplementation((url) => {
    if (url === '/marketing/overall-row-rules') {
      return Promise.resolve({ data: { rules: overallRules } })
    }
    if (url === '/marketing/broadband-rules') {
      return Promise.resolve({ data: broadbandRules })
    }
    if (url === '/marketing/organizations') {
      return Promise.resolve({
        data: {
          items: [
            { data_type: 'xszb', org_name: '热线运营组', row_label: '线上直办-热线', count: 1 },
            { data_type: 'fwgd', org_name: '区域组', row_label: '营销工单-区域', count: 2 }
          ]
        }
      })
    }
    if (url === '/marketing/row-rule-preview') {
      return Promise.resolve({ data: { unclassified: 1, samples: [] } })
    }
    if (url === '/marketing/broadband-rule-preview') {
      return Promise.resolve({
        data: {
          unclassified: 2,
          no_org: 1,
          samples: [{ emp_no: '--', org_name: '', count: 1 }]
        }
      })
    }
    if (url === '/marketing/key-products') {
      return Promise.resolve({ data: { products: [] } })
    }
    if (url === '/marketing/product-options') {
      return Promise.resolve({ data: { items: [] } })
    }
    return Promise.resolve({ data: {} })
  })
  api.put.mockImplementation((url) => {
    if (url === '/marketing/broadband-rules') {
      return Promise.resolve({ data: broadbandRules })
    }
    if (url === '/marketing/overall-row-rules') {
      return Promise.resolve({ data: { rules: overallRules } })
    }
    return Promise.resolve({ data: {} })
  })
})

describe('营销设置按数据源分组', () => {
  it('线上直办、办理工单、降套维系规则不再混在一起', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState

    expect(state.onlineRules.map((rule) => rule.id)).toEqual(['online-org'])
    expect(state.workOrderOrgRules.map((rule) => rule.id)).toEqual(['work-org'])
    expect(state.workOrderTenantRules.map((rule) => rule.id)).toEqual(['work-tenant'])
    expect(state.downgradeRules.map((rule) => rule.id)).toEqual(['downgrade'])
    expect(state.inheritedOnlineOrgRules).toHaveLength(1)
    expect(state.inheritedOnlineOrgRules[0].source).toBe('线上直办规则')
    expect(state.inheritedOnlineOrgRules[0].row_label).toBe('营销工单-热线')
    expect(state.broadbandRules.inherited_org_rules[0].source).toBe('线上直办规则')
  })

  it('宽带规则按组织机构 + 工号兜底分别保存', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState

    state.addBroadbandEmpRule()
    state.broadbandRules.emp_rules.at(-1).pattern = 'QYY'
    await state.saveBroadbandRules()

    expect(api.put).toHaveBeenCalledWith('/marketing/broadband-rules', {
      org_rules: broadbandRules.org_rules,
      emp_rules: [
        broadbandRules.emp_rules[0],
        expect.objectContaining({
          row_label: '营销工单-热线',
          match_type: 'equals',
          pattern: 'QYY'
        })
      ]
    })
  })

  it('各数据源可新增无需匹配内容的兜底规则', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState

    state.addOnlineFallbackRule()
    expect(state.config.rules.at(-1)).toMatchObject({
      row_label: '线上直办-工单',
      match_type: 'fallback',
      pattern: ''
    })
    expect(state.patternPlaceholder(state.config.rules.at(-1))).toContain('无需填写')

    state.addWorkOrderFallbackRule()
    expect(state.config.rules.at(-1)).toMatchObject({
      row_label: '营销工单-工单',
      match_type: 'fallback',
      pattern: ''
    })

    state.addDowngradeFallbackRule()
    expect(state.config.rules.at(-1)).toMatchObject({
      row_label: '降套维系',
      match_type: 'fallback',
      pattern: ''
    })

    state.addBroadbandFallbackRule()
    expect(state.broadbandRules.emp_rules.at(-1)).toMatchObject({
      row_label: '营销工单-工单',
      match_type: 'fallback',
      pattern: ''
    })
  })

  it('可从未分类宽带订单预览快速添加工号规则', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState
    const before = state.broadbandRules.emp_rules.length

    state.addEmpRuleFromSample({ emp_no: '--', org_name: '', count: 1 })
    state.addEmpRuleFromSample({ emp_no: 'QYY', org_name: '', count: 1 })

    expect(state.broadbandRules.emp_rules).toHaveLength(before + 2)
    expect(state.broadbandRules.emp_rules.at(-2)).toMatchObject({
      row_label: '营销工单-热线',
      match_type: 'equals',
      pattern: '--'
    })
    expect(state.broadbandRules.emp_rules.at(-1)).toMatchObject({
      row_label: '营销工单-热线',
      match_type: 'prefix',
      pattern: 'QYY'
    })
  })
})
