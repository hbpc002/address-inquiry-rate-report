import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { instance, getHandler, initMock } = vi.hoisted(() => {
  const handlers = {}
  const inst = {
    on: vi.fn((type, cb) => { handlers[type] = cb }),
    off: vi.fn(),
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
    getZr: vi.fn(() => ({}))
  }
  return {
    instance: inst,
    getHandler: (type) => handlers[type],
    initMock: vi.fn(() => inst)
  }
})

vi.mock('../src/utils/echarts', () => ({
  default: {
    use: vi.fn(),
    init: initMock
  }
}))

import Echart from '../src/components/Echart.vue'

async function mountEchart(props = {}) {
  const wrapper = mount(Echart, { props: { options: {}, ...props } })
  await flushPromises()
  return wrapper
}

function click(el, x, y) {
  el.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: x, clientY: y }))
}

function pointerDown(el, x, y, button = 0) {
  el.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true, button, clientX: x, clientY: y }))
}

describe('Echart 点击灵敏度（原生 DOM 点击 + 位移容差）', () => {
  beforeEach(() => {
    initMock.mockClear()
    instance.on.mockClear()
  })

  it('干净点击且 zrender 已派发参数：emit 一次并沿用组件参数', async () => {
    const wrapper = await mountEchart()

    const zrClick = getHandler('click')
    expect(zrClick).toBeTypeOf('function')

    const params = { componentType: 'series', name: '云网一组' }
    pointerDown(wrapper.element, 100, 100)
    zrClick(params)
    click(wrapper.element, 100, 100)

    const emitted = wrapper.emitted('click')
    expect(emitted).toHaveLength(1)
    expect(emitted[0][0]).toEqual(params)
  })

  it('干净点击但无 zrender 参数：emit { componentType: null, offsetX, offsetY }', async () => {
    const wrapper = await mountEchart()

    pointerDown(wrapper.element, 100, 100)
    click(wrapper.element, 102, 104)

    const emitted = wrapper.emitted('click')
    expect(emitted).toHaveLength(1)
    const payload = emitted[0][0]
    expect(payload.componentType).toBeNull()
    expect(typeof payload.offsetX).toBe('number')
    expect(typeof payload.offsetY).toBe('number')
  })

  it('拖动（位移超过容差）不触发 click，避免与平移冲突', async () => {
    const wrapper = await mountEchart()

    pointerDown(wrapper.element, 100, 100)
    click(wrapper.element, 140, 90)

    pointerDown(wrapper.element, 200, 200)
    click(wrapper.element, 201, 220)

    expect(wrapper.emitted('click')).toBeUndefined()
  })

  it('clickable=false 时不注册任何点击监听', async () => {
    const wrapper = await mountEchart({ clickable: false })

    expect(initMock).toHaveBeenCalled()
    expect(instance.on).not.toHaveBeenCalled()

    pointerDown(wrapper.element, 100, 100)
    click(wrapper.element, 100, 100)
    expect(wrapper.emitted('click')).toBeUndefined()
  })

  it('右健按下不参与点击判定', async () => {
    const wrapper = await mountEchart()

    pointerDown(wrapper.element, 100, 100, 2)
    click(wrapper.element, 100, 100)
    pointerDown(wrapper.element, 100, 100, 0)
    click(wrapper.element, 103, 102)

    expect(wrapper.emitted('click')).toHaveLength(1)
  })
})