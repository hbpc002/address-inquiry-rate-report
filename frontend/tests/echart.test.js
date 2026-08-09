import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('@/utils/echarts', () => ({
  default: { init: vi.fn() }
}))

import echarts from '../src/utils/echarts'
import Echart from '../src/components/Echart.vue'

class MockResizeObserver {
  static instances = []
  static observed = []

  constructor(callback) {
    this.callback = callback
    this._disconnected = false
    MockResizeObserver.instances.push(this)
  }

  observe(el) {
    this.el = el
    MockResizeObserver.observed.push(el)
  }

  disconnect() {
    this._disconnected = true
  }

  trigger() {
    if (this.callback) this.callback([], this)
  }
}

const makeInstance = () => {
  const inst = { setOption: vi.fn(), resize: vi.fn(), on: vi.fn(), dispose: vi.fn() }
  echarts.init.mockReturnValue(inst)
  echarts.init.mockClear()
  return inst
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0))

beforeEach(() => {
  MockResizeObserver.instances = []
  MockResizeObserver.observed = []
  window.ResizeObserver = MockResizeObserver
  globalThis.ResizeObserver = MockResizeObserver
})

afterEach(() => {
  delete window.ResizeObserver
  delete globalThis.ResizeObserver
  vi.clearAllMocks()
})

describe('Echart 组件 - 容器尺寸自适应', () => {
  it('挂载后初始化图表并开始观察容器', async () => {
    const inst = makeInstance()
    const wrapper = mount(Echart, { props: { options: { title: { text: 'x' } } } })
    await flush()

    expect(echarts.init).toHaveBeenCalled()
    expect(inst.setOption).toHaveBeenCalled()
    expect(MockResizeObserver.observed.length).toBe(1)
  })

  it('容器从隐藏变为可见触发 observer 时调用 resize（修复缩在一角）', async () => {
    const inst = makeInstance()
    const wrapper = mount(Echart, { props: { options: {} } })
    await flush()

    const container = wrapper.find('.echart-container').element
    Object.defineProperty(container, 'offsetWidth', { value: 800, configurable: true })
    MockResizeObserver.instances[0].trigger()

    expect(inst.resize).toHaveBeenCalled()
  })

  it('对 0 宽度的隐藏容器不执行空 resize', async () => {
    const inst = makeInstance()
    const wrapper = mount(Echart, { props: { options: {} } })
    await flush()

    MockResizeObserver.instances[0].trigger()

    expect(inst.resize).not.toHaveBeenCalled()
  })

  it('卸载时断开观察器并销毁图表实例', async () => {
    const inst = makeInstance()
    const wrapper = mount(Echart, { props: { options: {} } })
    await flush()

    const observer = MockResizeObserver.instances[0]
    wrapper.unmount()

    expect(observer._disconnected).toBe(true)
    expect(inst.dispose).toHaveBeenCalled()
  })
})