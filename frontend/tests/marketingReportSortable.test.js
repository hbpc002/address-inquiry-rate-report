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

const emptyStats = {
  total: 0,
  order_count: 0,
  inbound: 0,
  outbound: 0,
  overlay: 0,
  package_change: 0,
  people_count: 0
}

const tabs = ['employee', 'team', 'group', 'product', 'day']

const stubs = {
  'el-card': { template: '<div class="el-card-stub"><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button class="el-button-stub"><slot /></button>' },
  'el-form': { template: '<form class="el-form-stub"><slot /></form>' },
  'el-form-item': { template: '<div class="el-form-item-stub"><slot /></div>' },
  'el-radio-group': { template: '<div class="el-radio-group-stub"><slot /></div>' },
  'el-radio': { template: '<label class="el-radio-stub"><slot /></label>' },
  'el-date-picker': { template: '<input class="el-date-picker-stub" />' },
  'el-select': { template: '<div class="el-select-stub"><slot /></div>' },
  'el-option': { template: '<div class="el-option-stub" />' },
  'el-input': { template: '<input class="el-input-stub" />' },
  'el-row': { template: '<div class="el-row-stub"><slot /></div>' },
  'el-statistic': { template: '<div class="el-statistic-stub" />' },
  'el-tabs': {
    props: ['modelValue'],
    emits: ['update:modelValue', 'tab-change'],
    template: `<div class="el-tabs-stub">
      <button
        v-for="name in ['employee', 'team', 'group', 'product', 'day']"
        :key="name"
        class="tab-button"
        :data-name="name"
        @click="$emit('update:modelValue', name); $emit('tab-change', name)"
      >{{ name }}</button>
      <slot />
    </div>`
  },
  'el-tab-pane': { template: '<div class="el-tab-pane-stub" />' },
  'el-table': { template: '<table class="el-table-stub"><slot /></table>' },
  'el-table-column': {
    props: {
      prop: String,
      label: String,
      sortable: { type: Boolean, default: false }
    },
    template: '<col class="el-table-column-stub" :data-prop="prop != null ? String(prop) : \'\'" :data-label="label != null ? String(label) : \'\'" :data-sortable="sortable ? \'true\' : \'false\'" />'
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

describe('营销统计表格列排序', () => {
  beforeEach(() => {
    api.get.mockReset()
    api.get.mockResolvedValue({
      data: {
        stats: emptyStats,
        employees: [],
        teams: [],
        groups: [],
        products: [],
        days: [],
        options: { groups: [], teams: [], orgs: [], products: [], sources: [] }
      }
    })
  })

  it('每个维度的所有数据列都支持排序', async () => {
    const wrapper = await mountPage()

    for (const name of tabs) {
      await wrapper.find(`.tab-button[data-name="${name}"]`).trigger('click')
      await flushPromises()

      const columns = wrapper.findAll('.el-table-column-stub')
      expect(columns.length).toBeGreaterThan(0)

      const unsortable = columns.filter((column) => column.attributes('data-sortable') !== 'true')
      expect(unsortable.map((column) => column.attributes('data-label'))).toEqual([])
    }
  })
})
