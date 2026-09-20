<template>
  <el-container class="main-container">
    <el-aside :width="sidebarWidth">
      <div class="logo">
        <span v-show="!isCollapsed">{{ ui.labels.project_name }}</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="openedMenus"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/">
          <el-icon><House /></el-icon>
          <span>{{ ui.labels.dashboard }}</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('checkin_report')" index="/checkin-report">
          <el-icon><Tickets /></el-icon>
          <span>{{ ui.labels.checkin_report }}</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('workload_report')" index="/workload-report">
          <el-icon><DataBoard /></el-icon>
          <span>{{ ui.labels.workload_report }}</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('broadband_report')" index="/broadband-report">
          <el-icon><DataLine /></el-icon>
          <span>{{ ui.labels.broadband_report }}</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('reports')" index="/reports">
          <el-icon><DataAnalysis /></el-icon>
          <span>{{ ui.labels.reports }}</span>
        </el-menu-item>
        <el-sub-menu v-if="canViewData" index="data">
          <template #title>
            <el-icon><FolderOpened /></el-icon>
            <span>{{ ui.labels.menu_data }}</span>
          </template>
          <el-menu-item v-if="userStore.canView('schedules')" index="/schedules">
            <span>{{ ui.labels.schedules }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('employees')" index="/employees">
            <span>{{ ui.labels.employees }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('checkins')" index="/checkins">
            <span>{{ ui.labels.checkins }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('training_records')" index="/training-records">
            <span>{{ ui.labels.training_records }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('workload')" index="/workloads">
            <span>{{ ui.labels.workload }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('broadband')" index="/broadband-orders">
            <span>{{ ui.labels.broadband_orders }}</span>
          </el-menu-item>
        </el-sub-menu>
        <el-sub-menu v-if="canViewSystem" index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>{{ ui.labels.menu_system }}</span>
          </template>
          <el-menu-item v-if="userStore.canView('system')" index="/system">
            <span>{{ ui.labels.system }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('users')" index="/users">
            <span>{{ ui.labels.users }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('roles')" index="/roles">
            <span>{{ ui.labels.roles }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('work_hour_settings')" index="/work-hour-settings">
            <span>{{ ui.labels.work_hour_settings }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('salary_config')" index="/salary-settings">
            <span>{{ ui.labels.salary_config }}</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.canView('field_annotations')" index="/field-annotations">
            <span>{{ ui.labels.field_annotations }}</span>
          </el-menu-item>
        </el-sub-menu>
        <el-menu-item v-if="userStore.hasPermission('agent.use')" index="/agent">
          <el-icon><ChatDotRound /></el-icon>
          <span>{{ ui.labels.agent }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-left">
          <el-button link @click="toggleSidebar" style="color: #333; font-size: 20px;">
            <el-icon><Fold v-if="!isCollapsed" /><Expand v-else /></el-icon>
          </el-button>
        </div>
        <div class="header-right">
          <span>{{ userStore.user?.display_name || userStore.user?.username }}</span>
          <el-button type="primary" link @click="showChangePwd = true">修改密码</el-button>
          <el-button type="danger" link @click="handleLogout">登出</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="showChangePwd" title="修改密码" width="400px">
    <el-form :model="pwdForm" label-width="80px">
      <el-form-item label="原密码">
        <el-input v-model="pwdForm.oldPassword" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="pwdForm.newPassword" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showChangePwd = false">取消</el-button>
      <el-button type="primary" :loading="changing" @click="handleChangePwd">确定</el-button>
    </template>
  </el-dialog>

  <AgentLauncher />
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { House, Tickets, DataBoard, DataAnalysis, DataLine, FolderOpened, Setting, Fold, Expand, ChatDotRound } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AgentLauncher from '@/components/AgentLauncher.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const ui = useUiConfigStore()

const activeMenu = computed(() => route.path)
const showChangePwd = ref(false)
const changing = ref(false)
const pwdForm = ref({ oldPassword: '', newPassword: '' })

const SYSTEM_ITEMS = [
  { path: '/system', key: 'system' },
  { path: '/users', key: 'users' },
  { path: '/roles', key: 'roles' },
  { path: '/work-hour-settings', key: 'work_hour_settings' },
  { path: '/salary-settings', key: 'salary_config' },
  { path: '/field-annotations', key: 'field_annotations' },
]
const SYSTEM_PATHS = SYSTEM_ITEMS.map(i => i.path)
const canViewSystem = computed(() => SYSTEM_ITEMS.some(i => userStore.canView(i.key)))

const DATA_ITEMS = [
  { path: '/schedules', key: 'schedules' },
  { path: '/employees', key: 'employees' },
  { path: '/checkins', key: 'checkins' },
  { path: '/training-records', key: 'training_records' },
  { path: '/workloads', key: 'workload' },
  { path: '/broadband-orders', key: 'broadband' },
]
const DATA_PATHS = DATA_ITEMS.map(i => i.path)
const canViewData = computed(() => DATA_ITEMS.some(i => userStore.canView(i.key)))

const openedMenus = computed(() => {
  if (SYSTEM_PATHS.includes(activeMenu.value)) return ['system']
  if (DATA_PATHS.includes(activeMenu.value)) return ['data']
  return []
})

const isCollapsed = ref(false)
const sidebarWidth = computed(() => isCollapsed.value ? '64px' : '200px')
function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

onMounted(() => {
  ui.load()
})

async function handleChangePwd() {
  if (!pwdForm.value.oldPassword || !pwdForm.value.newPassword) {
    ElMessage.warning('请填写完整')
    return
  }
  changing.value = true
  try {
    await userStore.changePassword(pwdForm.value.oldPassword, pwdForm.value.newPassword)
    ElMessage.success('密码修改成功')
    showChangePwd.value = false
    pwdForm.value = { oldPassword: '', newPassword: '' }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    changing.value = false
  }
}
</script>

<style scoped>
.main-container {
  height: 100vh;
}

.el-aside {
  background-color: #304156;
  transition: width 0.3s ease;
  overflow: hidden;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
}

.el-header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.el-main {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>