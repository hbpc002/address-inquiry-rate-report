import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { computed, h, inject, provide } from 'vue'

vi.mock('../src/stores/user', () => {
  const get = vi.fn()
  const post = vi.fn()
  return {
    api: { get, post },
    useUserStore: vi.fn(() => ({
      hasPermission: vi.fn(() => true)
    }))
  }
})

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()) }
}))

import { api } from '../src/stores/user'
import DepartmentGroups from '../src/views/DepartmentGroups.vue'

const group = {
  id: 1,
  name: 'A部门组',
  description: '测试',
  paths: ['A部门'],
  user_count: 1,
  is_active: true
}

const tableStub = {
  name: 'ElTable',
  props: ['data'],
  emits: ['selection-change'],
  setup(props, { slots, emit }) {
    provide('tableRow', computed(() => (props.data && props.data[0]) || {}))
    return () => h('div', { class: 'el-table-stub' }, [
      h('button', {
        class: 'select-rows-stub',
        onClick: () => emit('selection-change', props.data || [])
      }, 'select'),
      ...(slots.default ? slots.default() : [])
    ])
  }
}

const tableColumnStub = {
  name: 'ElTableColumn',
  setup(_, { slots }) {
    const tableRow = inject('tableRow', computed(() => ({})))
    return () => h('div', { class: 'el-table-column-stub' }, slots.default
      ? slots.default({ row: tableRow.value })
      : [])
  }
}

const stubs = {
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-input': { template: '<input />' },
  'el-switch': { template: '<div />' },
  'el-dialog': { template: '<div class="el-dialog-stub"><slot /><slot name="footer" /></div>' },
  'el-tabs': { template: '<div class="el-tabs-stub"><slot /></div>' },
  'el-tab-pane': { template: '<div class="el-tab-pane-stub"><slot /></div>' },
  'el-alert': { template: '<div class="el-alert-stub" />' },
  'el-tag': { template: '<span class="el-tag-stub"><slot /></span>' },
  'el-select': {
    emits: ['update:modelValue'],
    template: '<div class="el-select-stub" @click="$emit(\'update:modelValue\', [2])"><slot /></div>'
  },
  'el-option': {
    props: ['label'],
    template: '<div class="el-option-stub">{{ label }}</div>'
  },
  'el-table': tableStub,
  'el-table-column': tableColumnStub,
  'el-pagination': { template: '<div />' },
  'el-button': {
    emits: ['click'],
    template: '<button class="el-button-stub" @click="$emit(\'click\')"><slot /></button>'
  }
}

function buttonByText(wrapper, text) {
  return wrapper.findAll('button').find(button => button.text().includes(text))
}

async function mountPage() {
  const wrapper = mount(DepartmentGroups, {
    global: {
      stubs,
      directives: { loading: {} }
    }
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.get.mockImplementation((url) => {
    if (url === '/department-groups') {
      return Promise.resolve({ data: { items: [group] } })
    }
    if (url.endsWith('/available-users')) {
      return Promise.resolve({
        data: [
          {
            id: 2,
            username: 'candidate',
            display_name: '候选用户',
            role: 'user',
            is_active: true,
            department_group_id: 9,
            department_group_name: '原部门组'
          }
        ]
      })
    }
    if (url.endsWith('/members')) {
      return Promise.resolve({
        data: {
          items: [
            { id: 3, username: 'member', display_name: '当前成员', role: 'user', is_active: true }
          ],
          total: 1
        }
      })
    }
    return Promise.resolve({ data: {} })
  })
  api.post.mockResolvedValue({ data: { assigned: 1, skipped: 0, removed: 1, user_count: 1 } })
})

describe('DepartmentGroups assignment dialog', () => {
  it('loads available users and current members when opening assignment', async () => {
    const wrapper = await mountPage()

    await buttonByText(wrapper, '分配人员').trigger('click')
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/department-groups/1/available-users', { params: { keyword: '' } })
    expect(api.get).toHaveBeenCalledWith('/department-groups/1/members', {
      params: { keyword: '', page: 1, limit: 10 }
    })
    expect(wrapper.text()).toContain('候选用户')
    expect(wrapper.text()).toContain('移出选中')
  })

  it('adds selected users to the department group', async () => {
    const wrapper = await mountPage()
    await buttonByText(wrapper, '分配人员').trigger('click')
    await flushPromises()

    await wrapper.find('.el-select-stub').trigger('click')
    await buttonByText(wrapper, '加入部门').trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/department-groups/1/members', { user_ids: [2] })
    expect(api.get).toHaveBeenCalledWith('/department-groups/1/members', expect.any(Object))
  })

  it('removes selected members from the department group', async () => {
    const wrapper = await mountPage()
    await buttonByText(wrapper, '分配人员').trigger('click')
    await flushPromises()

    const tables = wrapper.findAll('.el-table-stub')
    await tables[1].find('.select-rows-stub').trigger('click')
    await flushPromises()
    await buttonByText(wrapper, '移出选中').trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/department-groups/1/members/remove', { user_ids: [3] })
  })
})
