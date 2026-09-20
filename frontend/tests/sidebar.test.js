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
  'el-sub-menu': { template: '<div class="el-sub-menu-stub" :data-index="$attrs.index"><slot name="title" /><slot /></div>' },
  'el-menu-item-group': { template: '<div><slot /></div>' },
  'el-option': { template: '<div />' },
  Fold: { template: '<span class="fold-icon-stub" />' },
  Expand: { template: '<span class="expand-icon-stub" />' },
  House: { template: '<span class="icon-house" />' },
  User: { template: '<span class="icon-user" />' },
  Calendar: { template: '<span class="icon-calendar" />' },
  Clock: { template: '<span class="icon-clock" />' },
  Tickets: { template: '<span class="icon-tickets" />' },
  DataBoard: { template: '<span class="icon-data-board" />' },
  DataAnalysis: { template: '<span class="icon-data-analysis" />' },
  FolderOpened: { template: '<span class="icon-folder-opened" />' },
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

  const SYSTEM_LABELS = ['系统管理', '用户管理', '角色管理', '工时预警设置', '绩效配置', '字段批注']
  const DATA_LABELS = ['排班管理', '员工管理', '签到记录', '培训记录', '工作量详单']
  const TOP_LEVEL_LABELS = ['排班调度', '团队管理', '考勤报表', '哟你通通']
  const SYSTEM_PATHS = ['/system', '/users', '/roles', '/work-hour-settings', '/salary-settings', '/field-annotations']
  const DATA_PATHS = ['/schedules', '/employees', '/checkins', '/training-records', '/workloads']

  function submenuByIndex(index) {
    return wrapper.findAll('.el-sub-menu-stub').find(s => s.attributes('data-index') === index)
  }

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

  it('renders 系统设置 and 数据管理 submenus for admin users', () => {
    expect(submenuByIndex('system').exists()).toBe(true)
    expect(submenuByIndex('system').text()).toContain('系统设置')
    expect(submenuByIndex('data').exists()).toBe(true)
    expect(submenuByIndex('data').text()).toContain('数据管理')
  })

  it('places 数据管理 above 系统设置 in the menu', () => {
    const menu = wrapper.find('.el-menu-stub')
    const children = menu.element.children
    const dataIdx = menuzIndex(children, 'data')
    const sysIdx = menuzIndex(children, 'system')
    expect(dataIdx).toBeGreaterThanOrEqual(0)
    expect(sysIdx).toBeGreaterThanOrEqual(0)
    expect(dataIdx).toBeLessThan(sysIdx)
  })

  it('keeps system pages inside the submenu instead of top level', () => {
    const submenuText = submenuByIndex('system').text()
    for (const label of SYSTEM_LABELS) {
      expect(submenuText).toContain(label)
    }

    const topLevelText = topLevelTextOf(wrapper)
    for (const label of SYSTEM_LABELS) {
      expect(topLevelText).not.toContain(label)
    }
  })

  it('keeps data pages inside the 数据管理 submenu instead of top level', () => {
    const dataMenuText = submenuByIndex('data').text()
    for (const label of DATA_LABELS) {
      expect(dataMenuText).toContain(label)
    }

    const topLevelText = topLevelTextOf(wrapper)
    for (const label of DATA_LABELS) {
      expect(topLevelText).not.toContain(label)
    }
  })

  it('keeps remaining pages at the top level', () => {
    const topLevelText = topLevelTextOf(wrapper)
    for (const label of TOP_LEVEL_LABELS) {
      expect(topLevelText).toContain(label)
    }
  })

  it('does not bind grouped pages to the top-level router menu', () => {
    const indexes = wrapper.findAll('.el-menu-stub > .el-menu-item-stub').map(i => i.attributes('index'))
    for (const p of [...SYSTEM_PATHS, ...DATA_PATHS]) {
      expect(indexes).not.toContain(p)
    }
  })

  it('auto-opens the system submenu on a system page', async () => {
    await mountAt('/work-hour-settings')
    expect(wrapper.find('.el-menu-stub').attributes('data-openeds')).toContain('system')
  })

  it('auto-opens the data submenu on a data page', async () => {
    await mountAt('/workloads')
    expect(wrapper.find('.el-menu-stub').attributes('data-openeds')).toContain('data')
  })

  it('does not auto-open any submenu on top-level pages', () => {
    const opened = wrapper.find('.el-menu-stub').attributes('data-openeds') || ''
    expect(opened).not.toContain('system')
    expect(opened).not.toContain('data')
  })

  it('hides both submenus when the user has no permissions', async () => {
    userStore.user = { is_system: false, permissions: '{}' }
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('.el-sub-menu-stub').length).toBe(0)
  })

  it('shows only 数据管理 when only data permissions are granted', async () => {
    userStore.user = { is_system: false, permissions: JSON.stringify({ 'employees.view': true }) }
    await wrapper.vm.$nextTick()
    expect(submenuByIndex('data').exists()).toBe(true)
    expect(submenuByIndex('system')).toBeUndefined()
  })

  it('shows only 系统设置 when only system permissions are granted', async () => {
    userStore.user = { is_system: false, permissions: JSON.stringify({ 'work_hour_settings.view': true }) }
    await wrapper.vm.$nextTick()
    expect(submenuByIndex('system').exists()).toBe(true)
    expect(submenuByIndex('data')).toBeUndefined()
  })
})

function topLevelTextOf(wrapper) {
  return wrapper.findAll('.el-menu-stub > .el-menu-item-stub').map(i => i.text()).join('\n')
}

function menuzIndex(children, index) {
  for (let i = 0; i < children.length; i++) {
    if (children[i].getAttribute('data-index') === index) return i
  }
  return -1
}
