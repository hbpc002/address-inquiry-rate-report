import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

vi.mock('../src/stores/user', () => {
  const get = vi.fn()
  const post = vi.fn()
  const del = vi.fn()
  return {
    api: { get, post, delete: del },
    useUserStore: vi.fn(() => ({
      hasPermission: vi.fn(() => true)
    }))
  }
})

vi.mock('../src/stores/uiConfig', () => ({
  useUiConfigStore: vi.fn(() => ({
    labels: { training_records: '培训记录' }
  }))
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()) }
}))

vi.mock('@element-plus/icons-vue', () => ({
  UploadFilled: { template: '<span />' }
}))

import { api } from '../src/stores/user'
import TrainingRecords from '../src/views/TrainingRecords.vue'

const paginationStub = {
  name: 'ElPagination',
  props: ['currentPage', 'pageSize', 'total', 'pageSizes', 'layout'],
  emits: ['update:current-page', 'update:page-size', 'current-change', 'size-change'],
  template: '<div class="el-pagination-stub" />'
}

const stubs = {
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-space': { template: '<div><slot /></div>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-input': { template: '<input />' },
  'el-date-picker': { template: '<div />' },
  'el-time-picker': { template: '<div />' },
  'el-select': { template: '<div><slot /></div>' },
  'el-option': { template: '<div />' },
  'el-table': { template: '<div><slot /></div>' },
  'el-table-column': { template: '<div />' },
  'el-dialog': { template: '<div><slot /><slot name="footer" /></div>' },
  'el-upload': { template: '<div><slot /><slot name="tip" /></div>' },
  'el-icon': { template: '<span><slot /></span>' },
  'el-tag': { template: '<span><slot /></span>' },
  'el-button': {
    emits: ['click'],
    template: '<button class="el-button-stub" @click="$emit(\'click\')"><slot /></button>'
  },
  'el-pagination': paginationStub
}

async function mountPage() {
  const wrapper = mount(TrainingRecords, {
    global: { stubs }
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

function trainingCalls() {
  return api.get.mock.calls.filter(([url]) => url === '/training-records')
}

function buttonByText(wrapper, text) {
  return wrapper.findAll('button').find(button => button.text().includes(text))
}

beforeEach(() => {
  vi.clearAllMocks()
  api.get.mockImplementation((url) => {
    if (url === '/employees') {
      return Promise.resolve({ data: { items: [] } })
    }
    if (url === '/training-records') {
      return Promise.resolve({
        data: {
          items: [{ id: 1, emp_no: 'E001', record_date: '2026-11-01', type: '培训' }],
          total: 25,
          total_minutes: 1500
        }
      })
    }
    return Promise.resolve({ data: {} })
  })
})

describe('TrainingRecords pagination', () => {
  it('loads the first page by default and shows the filtered total', async () => {
    const wrapper = await mountPage()

    expect(trainingCalls()[0][1].params).toMatchObject({ page: 1, limit: 20 })

    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    expect(pagination.props('total')).toBe(25)
    expect(wrapper.text()).toContain('共 25 条记录')
    expect(wrapper.text()).toContain('总时长: 1500 分钟')
  })

  it('requests the selected page when pagination changes', async () => {
    const wrapper = await mountPage()
    const pagination = wrapper.findComponent({ name: 'ElPagination' })

    pagination.vm.$emit('update:current-page', 2)
    await nextTick()
    pagination.vm.$emit('current-change', 2)
    await flushPromises()

    expect(trainingCalls().at(-1)[1].params).toMatchObject({ page: 2, limit: 20 })
  })

  it('resets to the first page when page size changes', async () => {
    const wrapper = await mountPage()
    const pagination = wrapper.findComponent({ name: 'ElPagination' })

    pagination.vm.$emit('update:current-page', 3)
    await nextTick()
    pagination.vm.$emit('update:page-size', 50)
    await nextTick()
    pagination.vm.$emit('size-change', 50)
    await flushPromises()

    expect(trainingCalls().at(-1)[1].params).toMatchObject({ page: 1, limit: 50 })
  })

  it('resets to the first page when searching', async () => {
    const wrapper = await mountPage()
    const pagination = wrapper.findComponent({ name: 'ElPagination' })

    pagination.vm.$emit('update:current-page', 2)
    await nextTick()
    pagination.vm.$emit('current-change', 2)
    await flushPromises()

    await buttonByText(wrapper, '查询').trigger('click')
    await flushPromises()

    expect(trainingCalls().at(-1)[1].params).toMatchObject({ page: 1, limit: 20 })
  })
})
