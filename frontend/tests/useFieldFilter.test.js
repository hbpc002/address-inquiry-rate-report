import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import {
  useFieldFilter,
  matchesFieldConditions,
  applyFieldFilter,
  toComparableNumber
} from '../src/composables/useFieldFilter'

const fields = [
  { key: 'name', label: '姓名', unit: 'string', get: row => row.name },
  { key: 'ratio', label: '比率', unit: 'number', get: row => row.ratio ?? null },
  { key: 'percent', label: '百分比', unit: 'percent', get: row => (row.percent === null || row.percent === undefined) ? null : +(row.percent * 100).toFixed(2) }
]

function createWrapper(key, fieldDefs = fields) {
  const TestComp = defineComponent({
    setup() {
      return useFieldFilter(fieldDefs, { persistKey: key })
    },
    template: '<div></div>'
  })
  return mount(TestComp)
}

describe('useFieldFilter', () => {
  const KEY = 'test-field-filter'

  beforeEach(() => {
    sessionStorage.clear()
  })

  it('starts empty when no saved data', () => {
    const wrapper = createWrapper(KEY)
    expect(wrapper.vm.conditions).toEqual([])
    expect(wrapper.vm.activeCount).toBe(0)
  })

  it('adds and removes conditions', () => {
    const wrapper = createWrapper(KEY)
    wrapper.vm.addCondition()
    expect(wrapper.vm.conditions.length).toBe(1)
    expect(wrapper.vm.conditions[0]).toMatchObject({ fieldKey: 'name', operator: 'gt' })
    wrapper.vm.removeCondition(0)
    expect(wrapper.vm.conditions).toEqual([])
  })

  it('counts only active conditions', () => {
    const wrapper = createWrapper(KEY)
    wrapper.vm.conditions.push({ fieldKey: 'ratio', operator: 'gt', value: 12 })
    wrapper.vm.conditions.push({ fieldKey: 'name', operator: 'gt', value: null })
    expect(wrapper.vm.activeCount).toBe(1)
  })

  it('clears conditions and storage', () => {
    sessionStorage.setItem(KEY, JSON.stringify([{ fieldKey: 'percent', operator: 'gt', value: 3 }]))
    const wrapper = createWrapper(KEY)
    expect(wrapper.vm.conditions.length).toBe(1)
    wrapper.vm.clear()
    expect(wrapper.vm.conditions).toEqual([])
    expect(sessionStorage.getItem(KEY)).toBeNull()
  })

  it('restores persisted conditions', () => {
    sessionStorage.setItem(KEY, JSON.stringify([{ fieldKey: 'ratio', operator: 'ge', value: 20 }]))
    const wrapper = createWrapper(KEY)
    expect(wrapper.vm.conditions).toEqual([{ fieldKey: 'ratio', operator: 'ge', value: 20 }])
  })

  it('no crash on invalid persisted JSON', () => {
    sessionStorage.setItem(KEY, '{bad json}')
    const wrapper = createWrapper(KEY)
    expect(wrapper.vm.conditions).toEqual([])
  })
})

describe('toComparableNumber', () => {
  it('converts values to numbers', () => {
    expect(toComparableNumber('5')).toBe(5)
    expect(toComparableNumber('3.14')).toBe(3.14)
    expect(toComparableNumber(null)).toBeNull()
    expect(toComparableNumber(undefined)).toBeNull()
    expect(toComparableNumber('abc')).toBeNull()
    expect(toComparableNumber(7)).toBe(7)
  })
})

describe('matchesFieldConditions', () => {
  const row = { name: '张三', ratio: 30, percent: 0.9 }

  it('matches all AND conditions', () => {
    const conditions = [
      { fieldKey: 'ratio', operator: 'gt', value: 10 },
      { fieldKey: 'percent', operator: 'lt', value: 95 }
    ]
    expect(matchesFieldConditions(row, conditions, fields)).toBe(true)
  })

  it('fails when one condition is not met', () => {
    const conditions = [
      { fieldKey: 'ratio', operator: 'gt', value: 50 },
      { fieldKey: 'percent', operator: 'gt', value: 50 }
    ]
    expect(matchesFieldConditions(row, conditions, fields)).toBe(false)
  })

  it('supports gt/ge/lt/le operators', () => {
    expect(matchesFieldConditions(row, [{ fieldKey: 'ratio', operator: 'ge', value: 30 }], fields)).toBe(true)
    expect(matchesFieldConditions(row, [{ fieldKey: 'ratio', operator: 'gt', value: 30 }], fields)).toBe(false)
    expect(matchesFieldConditions(row, [{ fieldKey: 'ratio', operator: 'le', value: 30 }], fields)).toBe(true)
    expect(matchesFieldConditions(row, [{ fieldKey: 'ratio', operator: 'lt', value: 30 }], fields)).toBe(false)
  })

  it('excludes rows with null/missing values', () => {
    expect(matchesFieldConditions({ name: '李四', ratio: null, percent: null }, [{ fieldKey: 'percent', operator: 'gt', value: 10 }], fields)).toBe(false)
  })

  it('ignores empty conditions', () => {
    expect(matchesFieldConditions(row, [{ fieldKey: 'percent', operator: 'gt', value: '' }], fields)).toBe(true)
    expect(matchesFieldConditions(row, [], fields)).toBe(true)
  })

  it('computes percent via field get (percent stored as decimal -> 100 scale)', () => {
    expect(matchesFieldConditions(row, [{ fieldKey: 'percent', operator: 'ge', value: 90 }], fields)).toBe(true)
    expect(matchesFieldConditions(row, [{ fieldKey: 'percent', operator: 'gt', value: 95 }], fields)).toBe(false)
  })
})

describe('applyFieldFilter', () => {
  const data = [
    { name: 'a', ratio: 0.5, percent: 0.8 },
    { name: 'b', ratio: 0.9, percent: 0.6 },
    { name: 'c', ratio: 0.2, percent: 0.95 }
  ]

  it('returns data unchanged when no conditions', () => {
    expect(applyFieldFilter(data, [], fields)).toBe(data)
  })

  it('filters rows by conditions', () => {
    const result = applyFieldFilter(data, [{ fieldKey: 'percent', operator: 'ge', value: 80 }], fields)
    expect(result.map(r => r.name)).toEqual(['a', 'c'])
  })
})