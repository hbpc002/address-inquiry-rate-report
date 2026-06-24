import { describe, it, expect, beforeEach } from 'vitest'
import { ref, computed } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ path: '/' })),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}))

function createSidebarState() {
  const isCollapsed = ref(false)
  const sidebarWidth = computed(() => isCollapsed.value ? '64px' : '200px')
  function toggleSidebar() {
    isCollapsed.value = !isCollapsed.value
  }
  return { isCollapsed, sidebarWidth, toggleSidebar }
}

const minimalStubs = {
  'el-aside': { template: '<div :style="{ width: $attrs.width }" class="el-aside-stub"><slot /></div>', inheritAttrs: false },
  'el-menu': { template: '<div class="el-menu-stub"><slot /></div>' },
  'el-menu-item': { template: '<div class="el-menu-item-stub"><slot /></div>' },
  'el-icon': { template: '<span class="el-icon-stub"><slot /></span>' },
  'el-container': { template: '<div style="display:flex"><slot /></div>' },
  'el-header': { template: '<div style="display:flex"><slot /></div>' },
  'el-main': { template: '<main><slot /></main>' },
  'el-button': { template: '<button class="el-button-stub"><slot /></button>' },
  'el-dialog': { template: '<div v-if="modelValue" class="el-dialog-stub"><slot /></div>', props: ['modelValue'] },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-input': { template: '<input />' },
  'router-view': { template: '<div class="router-view-stub" />' },
  'router-link': { template: '<a><slot /></a>' },
  'el-sub-menu': { template: '<div><slot /></div>' },
  'el-menu-item-group': { template: '<div><slot /></div>' },
  'el-option': { template: '<div />' },
  Fold: { template: '<span class="fold-icon-stub" />' },
  Expand: { template: '<span class="expand-icon-stub" />' },
  House: { template: '<span class="icon-house" />' },
  User: { template: '<span class="icon-user" />' },
  Calendar: { template: '<span class="icon-calendar" />' },
  Clock: { template: '<span class="icon-clock" />' },
  Tickets: { template: '<span class="icon-tickets" />' },
  DataAnalysis: { template: '<span class="icon-data-analysis" />' },
  Setting: { template: '<span class="icon-setting" />' },
  UserFilled: { template: '<span class="icon-user-filled" />' },
  Warning: { template: '<span class="icon-warning" />' },
  Management: { template: '<span class="icon-management" />' },
}

describe('Sidebar Collapse Logic', () => {
  it('should start expanded with width 200px', () => {
    const state = createSidebarState()
    expect(state.sidebarWidth.value).toBe('200px')
    expect(state.isCollapsed.value).toBe(false)
  })

  it('should toggle to collapsed width 64px', () => {
    const state = createSidebarState()
    state.toggleSidebar()
    expect(state.sidebarWidth.value).toBe('64px')
    expect(state.isCollapsed.value).toBe(true)
  })

  it('should toggle back to expanded width 200px', () => {
    const state = createSidebarState()
    state.toggleSidebar()
    state.toggleSidebar()
    expect(state.sidebarWidth.value).toBe('200px')
    expect(state.isCollapsed.value).toBe(false)
  })

  it('should toggle correctly after multiple clicks', () => {
    const state = createSidebarState()
    const expected = [true, false, true, false]
    for (const exp of expected) {
      state.toggleSidebar()
      expect(state.isCollapsed.value).toBe(exp)
    }
  })
})

describe('Main.vue Sidebar Integration', () => {
  let wrapper

  beforeEach(async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const Main = (await import('../src/views/Main.vue')).default
    wrapper = mount(Main, {
      global: { plugins: [pinia], stubs: minimalStubs },
      attachTo: document.body,
    })
  })

  it('should render sidebar expanded by default', () => {
    const aside = wrapper.find('.el-aside-stub')
    expect(aside.attributes('style')).toContain('width: 200px')
  })

  it('should toggle sidebar when toggle button is clicked', async () => {
    const aside = wrapper.find('.el-aside-stub')
    const btn = wrapper.find('.el-button-stub')

    expect(aside.attributes('style')).toContain('width: 200px')

    await btn.trigger('click')
    expect(aside.attributes('style')).toContain('width: 64px')

    await btn.trigger('click')
    expect(aside.attributes('style')).toContain('width: 200px')
  })

  it('should toggle the Fold/Expand icon', async () => {
    expect(wrapper.find('.fold-icon-stub').exists()).toBe(true)
    expect(wrapper.find('.expand-icon-stub').exists()).toBe(false)

    await wrapper.find('.el-button-stub').trigger('click')

    expect(wrapper.find('.fold-icon-stub').exists()).toBe(false)
    expect(wrapper.find('.expand-icon-stub').exists()).toBe(true)
  })

  it('should show/hide logo text when toggling', async () => {
    const logoText = wrapper.find('.logo span')
    expect(logoText.isVisible()).toBe(true)

    await wrapper.find('.el-button-stub').trigger('click')

    expect(logoText.isVisible()).toBe(false)
  })
})
