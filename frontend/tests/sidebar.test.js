import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { ref, computed } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useRoute } from 'vue-router'
import { useUserStore } from '../src/stores/user'

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
  'el-menu': { template: '<div class="el-menu-stub" :data-openeds="defaultOpeneds">\n<slot /></div>', props: ['defaultActive', 'defaultOpeneds', 'collapse'] },
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
  'el-sub-menu': { template: '<div class="el-sub-menu-stub"><slot name="title" /><slot /></div>' },
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

describe('Main.vue Menu Grouping', () => {
  let wrapper
  let userStore

  const SYSTEM_LABELS = ['系统管理', '用户管理', '角色管理', '绩效配置', '字段批注']
  const TOP_LEVEL_LABELS = ['员工管理', '排班管理', '签到记录', '培训记录', '工作量详单', '工时预警设置', '考勤报表']

  beforeEach(async () => {
    vi.mocked(useRoute).mockReturnValue({ path: '/' })
    const pinia = createPinia()
    setActivePinia(pinia)
    userStore = useUserStore()
    userStore.user = { is_system: true }
    const Main = (await import('../src/views/Main.vue')).default
    wrapper = mount(Main, {
      global: { plugins: [pinia], stubs: minimalStubs },
      attachTo: document.body,
    })
  })

  afterEach(() => {
    wrapper.unmount()
    vi.mocked(useRoute).mockReturnValue({ path: '/' })
  })

  async function mountAt(path) {
    vi.mocked(useRoute).mockReturnValue({ path })
    wrapper?.unmount()
    const pinia = createPinia()
    setActivePinia(pinia)
    userStore = useUserStore()
    userStore.user = { is_system: true }
    const Main = (await import('../src/views/Main.vue')).default
    wrapper = mount(Main, {
      global: { plugins: [pinia], stubs: minimalStubs },
      attachTo: document.body,
    })
  }

  it('renders a 系统设置 submenu for admin users', () => {
    const submenu = wrapper.find('.el-sub-menu-stub')
    expect(submenu.exists()).toBe(true)
    expect(submenu.text()).toContain('系统设置')
  })

  it('keeps system pages inside the submenu instead of top level', () => {
    const submenuText = wrapper.find('.el-sub-menu-stub').text()
    for (const label of SYSTEM_LABELS) {
      expect(submenuText).toContain(label)
    }

    const topLevel = wrapper.findAll('.el-menu-stub > .el-menu-item-stub')
    const topLevelText = topLevel.map(i => i.text()).join('\n')
    for (const label of SYSTEM_LABELS) {
      expect(topLevelText).not.toContain(label)
    }
  })

  it('keeps non-system pages at the top level', () => {
    const topLevel = wrapper.findAll('.el-menu-stub > .el-menu-item-stub')
    const topLevelText = topLevel.map(i => i.text()).join('\n')
    for (const label of TOP_LEVEL_LABELS) {
      expect(topLevelText).toContain(label)
    }
  })

  it('does not bind system pages to the top-level router menu', () => {
    const topLevel = wrapper.findAll('.el-menu-stub > .el-menu-item-stub')
    const indexes = topLevel.map(i => i.attributes('index'))
    expect(indexes).not.toContain('/system')
    expect(indexes).not.toContain('/users')
    expect(indexes).not.toContain('/roles')
    expect(indexes).not.toContain('/salary-settings')
    expect(indexes).not.toContain('/field-annotations')
  })

  it('auto-opens the submenu when current route is a system page', async () => {
    await mountAt('/field-annotations')
    expect(wrapper.find('.el-menu-stub').attributes('data-openeds')).toContain('system')
  })

  it('does not auto-open the submenu on non-system pages', () => {
    const opened = wrapper.find('.el-menu-stub').attributes('data-openeds') || ''
    expect(opened).not.toContain('system')
  })

  it('hides the submenu when the user has no system permissions', async () => {
    userStore.user = { is_system: false, permissions: '{}' }
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.el-sub-menu-stub').exists()).toBe(false)
  })

  it('hides submenu when only non-system permissions are granted', async () => {
    const perms = {}
    perms['employees.view'] = true
    userStore.user = { is_system: false, permissions: JSON.stringify(perms) }
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.el-sub-menu-stub').exists()).toBe(false)
  })
})
