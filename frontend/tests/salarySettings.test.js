import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('../src/stores/user', () => {
  const get = vi.fn()
  const put = vi.fn()
  return {
    api: { get, put },
    useUserStore: vi.fn(() => ({
      hasPermission: vi.fn(() => true)
    }))
  }
})

vi.mock('../src/stores/uiConfig', () => ({
  useUiConfigStore: vi.fn(() => ({
    labels: { salary_config: '绩效配置' },
    loaded: true
  }))
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()) }
}))

import { api } from '../src/stores/user'
import SalarySettings from '../src/views/SalarySettings.vue'

const stubs = {
  'el-card': { template: '<div class="el-card-stub"><slot name="header" /><slot /></div>' },
  'el-color-picker': { template: '<div class="el-color-picker-stub" />' },
  'el-dialog': { template: '<div class="el-dialog-stub"><slot /></div>' },
  'el-divider': {
    props: ['contentPosition'],
    template: '<div class="el-divider-stub" :data-content-position="contentPosition"><slot /></div>'
  },
  'el-form': { template: '<form class="el-form-stub"><slot /></form>' },
  'el-form-item': {
    props: ['label'],
    template: '<div class="el-form-item-stub"><span class="el-form-item-label">{{ label }}</span><slot /></div>'
  },
  'el-input': { template: '<input type="text" class="el-input-stub" />' },
  'el-input-number': {
    props: ['modelValue'],
    template: '<div class="el-input-number-stub" :data-value="String(modelValue)">{{ modelValue }}</div>'
  },
  'el-option': { props: ['value', 'label'], template: '<div class="el-option-stub">{{ label }}</div>' },
  'el-option-group': { props: ['label'], template: '<div class="el-option-group-stub"><slot /></div>' },
  'el-select': { template: '<div class="el-select-stub"><slot /></div>' },
  'el-switch': { template: '<div class="el-switch-stub" />' },
  'el-table': { template: '<table class="el-table-stub"><slot /></table>' },
  'el-table-column': { template: '<col class="el-table-column-stub" />' },
  'el-button': {
    emits: ['click'],
    template: '<button class="el-button-stub" @click="$emit(\'click\')"><slot /></button>'
  }
}

function salaryConfigItems(pointsFormula) {
  return [
    { rule_key: 'call_salary_tiers', rule_data: { tiers: [] } },
    { rule_key: 'sat_salary', rule_data: { coefficient: 0.5 } },
    { rule_key: 'call_gap_targets', rule_data: { targets: [2000, 2500, 3000] } },
    { rule_key: 'sat_diff', rule_data: { coeff_a: 19, coeff_b: 20 } },
    { rule_key: 'metric_targets', rule_data: { targets: [] } },
    { rule_key: 'points_formula', rule_data: pointsFormula }
  ]
}

async function mountPage() {
  const wrapper = mount(SalarySettings, {
    global: {
      stubs,
      directives: { loading: {} }
    }
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

function numberValueByLabel(wrapper, label) {
  const item = wrapper.findAll('.el-form-item-stub').find(i => i.text().includes(label))
  return item ? item.find('.el-input-number-stub').attributes('data-value') : null
}

function buttonByText(wrapper, text) {
  return wrapper.findAll('.el-button-stub').find(b => b.text().includes(text))
}

describe('绩效配置 - 宽带营销积分设置', () => {
  beforeEach(() => {
    api.get.mockReset()
    api.put.mockReset()
    api.get.mockImplementation((url) => {
      if (url === '/salary-config') {
        return Promise.resolve({ data: { items: salaryConfigItems({ recommend_coeff: 2, completed_coeff: 10 }) } })
      }
      return Promise.resolve({ data: [] })
    })
    api.put.mockResolvedValue({ data: {} })
  })

  it('配置页包含「宽带营销积分设置」区块与公式提示', async () => {
    const wrapper = await mountPage()
    const dividers = wrapper.findAll('.el-divider-stub')
    expect(dividers.some(d => d.text().includes('宽带营销积分设置'))).toBe(true)
    expect(wrapper.text()).toContain('宽带营销积分 = 推荐量 × 2 + 成功推荐 × 10')
  })

  it('默认回填推荐量系数 2、成功推荐系数 10', async () => {
    const wrapper = await mountPage()
    expect(numberValueByLabel(wrapper, '推荐量系数')).toBe('2')
    expect(numberValueByLabel(wrapper, '成功推荐系数')).toBe('10')
  })

  it('加载后端已保存的积分系数', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/salary-config') {
        return Promise.resolve({ data: { items: salaryConfigItems({ recommend_coeff: 3, completed_coeff: 5 }) } })
      }
      return Promise.resolve({ data: [] })
    })
    const wrapper = await mountPage()
    expect(numberValueByLabel(wrapper, '推荐量系数')).toBe('3')
    expect(numberValueByLabel(wrapper, '成功推荐系数')).toBe('5')
    expect(wrapper.text()).toContain('宽带营销积分 = 推荐量 × 3 + 成功推荐 × 5')
  })

  it('保存配置时提交 points_formula 规则', async () => {
    const wrapper = await mountPage()
    await buttonByText(wrapper, '保存配置').trigger('click')
    await flushPromises()

    const call = api.put.mock.calls.find(c => c[0] === '/salary-config/points_formula')
    expect(call).toBeTruthy()
    expect(call[1]).toEqual({ rule_data: { recommend_coeff: 2, completed_coeff: 10 } })
  })

  it('重置为默认：积分系数回到 2 / 10', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/salary-config') {
        return Promise.resolve({ data: { items: salaryConfigItems({ recommend_coeff: 8, completed_coeff: 9 }) } })
      }
      return Promise.resolve({ data: [] })
    })
    const wrapper = await mountPage()
    expect(numberValueByLabel(wrapper, '推荐量系数')).toBe('8')

    await buttonByText(wrapper, '重置为默认').trigger('click')
    await flushPromises()

    expect(numberValueByLabel(wrapper, '推荐量系数')).toBe('2')
    expect(numberValueByLabel(wrapper, '成功推荐系数')).toBe('10')
  })
})
