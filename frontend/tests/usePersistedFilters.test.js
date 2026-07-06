import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { usePersistedFilters } from '../src/composables/usePersistedFilters'

function createWrapper(key, defaults) {
  const TestComp = defineComponent({
    setup() {
      return usePersistedFilters(key, defaults)
    },
    template: '<div></div>'
  })
  return mount(TestComp)
}

describe('usePersistedFilters', () => {
  const KEY = 'test-persisted-filters'

  beforeEach(() => {
    sessionStorage.clear()
  })

  it('returns defaults when no saved data', () => {
    const wrapper = createWrapper(KEY, { name: 'default', count: 0 })
    expect(wrapper.vm.filters.name).toBe('default')
    expect(wrapper.vm.filters.count).toBe(0)
    expect(wrapper.vm.isRestored).toBe(false)
  })

  it('restores saved data from sessionStorage', () => {
    sessionStorage.setItem(KEY, JSON.stringify({ name: 'saved', count: 42 }))
    const wrapper = createWrapper(KEY, { name: 'default', count: 0 })
    expect(wrapper.vm.filters.name).toBe('saved')
    expect(wrapper.vm.filters.count).toBe(42)
    expect(wrapper.vm.isRestored).toBe(true)
  })

  it('merges partial saved data with defaults', () => {
    sessionStorage.setItem(KEY, JSON.stringify({ name: 'partial' }))
    const wrapper = createWrapper(KEY, { name: 'default', count: 10 })
    expect(wrapper.vm.filters.name).toBe('partial')
    expect(wrapper.vm.filters.count).toBe(10)
    expect(wrapper.vm.isRestored).toBe(true)
  })

  it('does not crash on invalid JSON in sessionStorage', () => {
    sessionStorage.setItem(KEY, '{invalid json}')
    const wrapper = createWrapper(KEY, { name: 'safe', count: 1 })
    expect(wrapper.vm.filters.name).toBe('safe')
    expect(wrapper.vm.filters.count).toBe(1)
    expect(wrapper.vm.isRestored).toBe(false)
  })

  it('clears corrupted sessionStorage data on parse failure', () => {
    sessionStorage.setItem(KEY, 'not-json')
    createWrapper(KEY, { name: 'x' })
    expect(sessionStorage.getItem(KEY)).toBeNull()
  })

  it('handles null/undefined saved value gracefully', () => {
    sessionStorage.setItem(KEY, null)
    const wrapper = createWrapper(KEY, { name: 'fallback' })
    expect(wrapper.vm.filters.name).toBe('fallback')
  })

  it('resets filters and removes storage', () => {
    sessionStorage.setItem(KEY, JSON.stringify({ name: 'stored' }))
    const wrapper = createWrapper(KEY, { name: 'default' })
    expect(wrapper.vm.filters.name).toBe('stored')
    wrapper.vm.resetFilters()
    expect(wrapper.vm.filters.name).toBe('default')
    expect(sessionStorage.getItem(KEY)).toBeNull()
  })
})
