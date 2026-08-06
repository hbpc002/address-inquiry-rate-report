import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import FieldFilterPanel from '../src/components/FieldFilterPanel.vue'

const fields = [
  { key: 'ratio', label: '比率', unit: 'number' },
  { key: 'percent', label: '百分比', unit: 'percent' }
]

const stubs = {
  'el-popover': { template: '<div><slot name="reference" /><div v-if="true"><slot /></div></div>' },
  'el-button': { template: '<button><slot /></button>' },
  'el-select': { template: '<div><slot /></div>' },
  'el-option': { template: '<span></span>' },
  'el-input-number': { template: '<input />' },
  'el-icon': { template: '<span><slot /></span>' },
  'el-badge': { template: '<span><slot /></span>' }
}

// Records the props passed to each stubbed el-select so we can assert that the
// dropdowns stay inline (teleported=false) and do not close the popover.
const selectProps = []
stubs['el-select'] = {
  props: ['teleported', 'modelValue'],
  setup(props) {
    selectProps.push(props)
  },
  template: '<div><slot /></div>'
}

// Captures the props passed to the stubbed el-popover so we can assert the
// two-way `visible` binding (update:visible handler) is present.
const popoverProps = []
stubs['el-popover'] = {
  props: ['modelValue', 'visible', 'onUpdate:visible'],
  emits: ['update:visible'],
  setup(props, { emit, expose }) {
    expose({ emitVisible: (v) => emit('update:visible', v), props })
    popoverProps.push(props)
  },
  template: '<div><slot name="reference" /><div v-if="true"><slot /></div></div>'
}

function mountPanel({ modelValue = [], persistKey = '' } = {}) {
  return mount(FieldFilterPanel, {
    props: { fields, modelValue, persistKey },
    global: { stubs }
  })
}

describe('FieldFilterPanel', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('renders the trigger button', () => {
    const wrapper = mountPanel()
    expect(wrapper.text()).toContain('字段筛选')
  })

  it('adds a condition to the local list', () => {
    const wrapper = mountPanel()
    wrapper.vm.addCondition()
    expect(wrapper.vm.localConditions.length).toBe(1)
    expect(wrapper.vm.localConditions[0]).toMatchObject({ fieldKey: 'ratio', operator: 'gt', unit: 'number' })
  })

  it('removes a condition', () => {
    const wrapper = mountPanel()
    wrapper.vm.addCondition()
    wrapper.vm.removeCondition(0)
    expect(wrapper.vm.localConditions.length).toBe(0)
  })

  it('emits cleared modelValue on clear and removes storage', () => {
    sessionStorage.setItem('panel-test-key', JSON.stringify([{ fieldKey: 'ratio', operator: 'gt', value: 5 }]))
    const wrapper = mountPanel({ modelValue: [{ fieldKey: 'ratio', operator: 'gt', value: 5 }], persistKey: 'panel-test-key' })
    wrapper.vm.clear()
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted.at(-1)[0]).toEqual([])
    expect(sessionStorage.getItem('panel-test-key')).toBeNull()
  })

  it('confirms and emits cleaned conditions', () => {
    const wrapper = mountPanel()
    wrapper.vm.addCondition()
    wrapper.vm.localConditions[0] = { ...wrapper.vm.localConditions[0], fieldKey: 'percent', operator: 'ge', value: 90 }
    wrapper.vm.confirm()
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted.at(-1)[0]).toEqual([{ fieldKey: 'percent', operator: 'ge', value: 90, unit: 'percent' }])
    expect(wrapper.vm.visible).toBe(false)
  })

  it('drops incomplete conditions on confirm', () => {
    const wrapper = mountPanel()
    wrapper.vm.addCondition()
    wrapper.vm.localConditions[0] = { ...wrapper.vm.localConditions[0], fieldKey: 'ratio', value: null }
    wrapper.vm.addCondition()
    wrapper.vm.localConditions[1] = { ...wrapper.vm.localConditions[1], fieldKey: 'percent', operator: 'lt', value: 5 }
    wrapper.vm.confirm()
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted.at(-1)[0]).toEqual([{ fieldKey: 'percent', operator: 'lt', value: 5, unit: 'percent' }])
  })

  it('syncs unit on field change', () => {
    const wrapper = mountPanel()
    wrapper.vm.addCondition()
    wrapper.vm.localConditions[0].fieldKey = 'percent'
    wrapper.vm.syncUnit(wrapper.vm.localConditions[0])
    expect(wrapper.vm.localConditions[0].unit).toBe('percent')
  })

  it('accumulates activeCount only for complete rows', () => {
    const wrapper = mountPanel()
    wrapper.vm.addCondition()
    expect(wrapper.vm.activeCount).toBe(0)
    wrapper.vm.localConditions[0] = { ...wrapper.vm.localConditions[0], fieldKey: 'ratio', value: 10 }
    expect(wrapper.vm.activeCount).toBe(1)
  })

  it('binds visible with a two-way update handler (fix: popover click opens)', () => {
    popoverProps.length = 0
    const wrapper = mountPanel()
    const props = popoverProps.at(-1)
    expect(props).toBeTruthy()
    expect(typeof props['onUpdate:visible']).toBe('function')
    // Simulating the popover's open -> emit update:visible sets the panel's visible ref
    expect(wrapper.vm.visible).toBe(false)
    props['onUpdate:visible'](true)
    expect(wrapper.vm.visible).toBe(true)
  })

  it('renders selects with teleported=false so dropdown clicks keep the popover open (fix: dropdown click hides panel)', () => {
    selectProps.length = 0
    const wrapper = mountPanel({ modelValue: [{ fieldKey: 'ratio', operator: 'gt', value: 5 }] })
    expect(selectProps.length).toBeGreaterThan(0)
    selectProps.forEach(p => {
      expect(p.teleported).toBe(false)
    })
  })
})