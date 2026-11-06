import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('../src/stores/user', () => {
  const get = vi.fn()
  const post = vi.fn()
  const del = vi.fn()
  return {
    api: { get, post, delete: del },
    useUserStore: vi.fn(() => ({ hasPermission: vi.fn(() => true) }))
  }
})

vi.mock('../src/stores/uiConfig', () => ({
  useUiConfigStore: vi.fn(() => ({
    labels: { marketing_opening: '开口率明细' },
    loaded: true
  }))
}))

vi.mock('../src/utils/download', () => ({ downloadBlob: vi.fn() }))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), warning: vi.fn(), success: vi.fn() },
  ElMessageBox: { confirm: vi.fn() }
}))

import { api } from '../src/stores/user'
import { downloadBlob } from '../src/utils/download'
import MarketingOpenings from '../src/views/MarketingOpenings.vue'

const item = {
  id: 1,
  contact_id: 'C1',
  record_time: '2026-11-02 09:00:00',
  record_date: '2026-11-02',
  emp_no: 'KF001',
  name: '张三',
  team: '10010热线客服代表',
  system_team: '热线1组',
  active_overlay: '是',
  opened_overlay: '是',
  active_broadband: '否',
  opened_broadband: '否',
  active_mobile_new: '否',
  opened_mobile_new: '否',
  active_terminal: '否',
  opened_terminal: '否',
  active_package: '否',
  opened_package: '否',
  five_products_opened: '是',
  import_batch: 'abc12345'
}

const stubs = {
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button><slot /></button>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-date-picker': { template: '<input />' },
  'el-select': { template: '<div><slot /></div>' },
  'el-option': { template: '<div />' },
  'el-input': { template: '<input />' },
  'el-space': { template: '<div><slot /></div>' },
  'el-table': { template: '<table><slot /></table>' },
  'el-table-column': {
    props: ['prop', 'label'],
    template: '<col :data-prop="prop != null ? String(prop) : \'\'" :data-label="label != null ? String(label) : \'\'" />'
  },
  'el-pagination': { template: '<div />' },
  'el-dialog': { template: '<div><slot /><slot name="footer" /></div>' },
  'el-upload': { template: '<div><slot /><slot name="tip" /></div>' },
  'el-icon': { template: '<i><slot /></i>' },
  'el-tag': { template: '<span><slot /></span>' }
}

async function mountPage() {
  const wrapper = mount(MarketingOpenings, { global: { stubs } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('开口率明细', () => {
  beforeEach(() => {
    api.get.mockReset()
    api.post.mockReset()
    api.delete.mockReset()
    downloadBlob.mockReset()
    api.get.mockResolvedValue({ data: { items: [item], total: 1 } })
  })

  it('加载原始明细并展示O-X十列', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState
    expect(api.get).toHaveBeenCalledWith('/marketing-openings', {
      params: expect.objectContaining({ page: 1, limit: 20 })
    })
    expect(state.tableData).toHaveLength(1)
    expect(state.openingColumns).toHaveLength(10)
    expect(state.openingColumns.map(column => column.key)).toEqual([
      'active_overlay', 'opened_overlay', 'active_broadband', 'opened_broadband',
      'active_mobile_new', 'opened_mobile_new', 'active_terminal', 'opened_terminal',
      'active_package', 'opened_package'
    ])
    expect(wrapper.text()).toContain('开口率明细')
  })

  it('按筛选条件导出明细', async () => {
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState
    state.searchForm.emp_no = 'KF001'
    state.range = ['2026-11-01', '2026-11-30']
    state.handleExport()
    expect(downloadBlob).toHaveBeenCalledWith(
      '/marketing-openings/export',
      {
        emp_no: 'KF001',
        start_date: '2026-11-01',
        end_date: '2026-11-30'
      },
      '开口率明细.csv'
    )
  })

  it('上传质检台文件后调用导入接口并刷新', async () => {
    api.post.mockResolvedValue({ data: { count: 1, skipped: 0, batch: 'abc12345' } })
    const wrapper = await mountPage()
    const state = wrapper.vm.$.setupState
    state.fileList = [{ name: '大模型质检台导出.csv', raw: new Blob(['x']) }]
    await state.handleUpload()
    expect(api.post).toHaveBeenCalledWith('/marketing-openings/import', expect.any(FormData), {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    expect(state.uploadResults[0].count).toBe(1)
  })
})
