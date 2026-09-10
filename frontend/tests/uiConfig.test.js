import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/stores/user', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
  },
}))

import { api } from '@/stores/user'
import { useUiConfigStore } from '@/stores/uiConfig'

const DEFAULTS = {
  project_name: '客户服务中心运营管理平台',
  dashboard: '工效仪表盘',
  checkin_report: '排班调度',
  workload_report: '团队管理',
  agent: '哟你通通',
}

describe('uiConfig store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    document.title = ''
  })

  it('无配置时使用默认名称', () => {
    const store = useUiConfigStore()
    expect(store.labels.project_name).toBe(DEFAULTS.project_name)
    expect(store.labels.dashboard).toBe('工效仪表盘')
    expect(store.labels.checkin_report).toBe('排班调度')
    expect(store.labels.workload_report).toBe('团队管理')
    expect(store.labels.agent).toBe('哟你通通')
  })

  it('load() 合并后端返回的名称并更新浏览器标题', async () => {
    api.get.mockResolvedValue({ data: { dashboard: '数据看板' } })
    const store = useUiConfigStore()
    await store.load()
    expect(api.get).toHaveBeenCalledWith('/ui-labels')
    expect(store.labels.dashboard).toBe('数据看板')
    expect(store.labels.project_name).toBe(DEFAULTS.project_name)
    expect(document.title).toBe(DEFAULTS.project_name)
  })

  it('load() 接口失败时回退默认', async () => {
    api.get.mockRejectedValue(new Error('network'))
    const store = useUiConfigStore()
    await store.load()
    expect(store.labels.dashboard).toBe('工效仪表盘')
    expect(store.loaded).toBe(true)
  })

  it('update() 提交修改并应用到本地与浏览器标题', async () => {
    api.put.mockResolvedValue({ data: { ...DEFAULTS, agent: '小助手' } })
    const store = useUiConfigStore()
    const result = await store.update({ agent: '小助手' })
    expect(api.put).toHaveBeenCalledWith('/ui-labels', { agent: '小助手' })
    expect(result.agent).toBe('小助手')
    expect(store.labels.agent).toBe('小助手')
  })

  it('setLabels / applyTitle 联动 document.title', () => {
    const store = useUiConfigStore()
    store.setLabels({ project_name: '测试平台' })
    expect(document.title).toBe('测试平台')
  })
})