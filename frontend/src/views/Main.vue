<template>
  <el-container class="main-container">
    <el-aside :width="sidebarWidth">
      <div class="logo">
        <span v-show="!isCollapsed">排班签到系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/">
          <el-icon><House /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('employees')" index="/employees">
          <el-icon><User /></el-icon>
          <span>员工管理</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('schedules')" index="/schedules">
          <el-icon><Calendar /></el-icon>
          <span>排班管理</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('checkins')" index="/checkins">
          <el-icon><Clock /></el-icon>
          <span>签到记录</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('checkin_report')" index="/checkin-report">
          <el-icon><Tickets /></el-icon>
          <span>签入签出报表</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('training_records')" index="/training-records">
          <el-icon><EditPen /></el-icon>
          <span>培训记录</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('workload')" index="/workloads">
          <el-icon><Document /></el-icon>
          <span>工作量详单</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('workload_report')" index="/workload-report">
          <el-icon><DataBoard /></el-icon>
          <span>工作量报表</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('work_hour_settings')" index="/work-hour-settings">
          <el-icon><Warning /></el-icon>
          <span>工时预警设置</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('reports')" index="/reports">
          <el-icon><DataAnalysis /></el-icon>
          <span>考勤报表</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('system')" index="/system">
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('users')" index="/users">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('roles')" index="/roles">
          <el-icon><Management /></el-icon>
          <span>角色管理</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('salary_config')" index="/salary-settings">
          <el-icon><Coin /></el-icon>
          <span>绩效配置</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.canView('field_annotations')" index="/field-annotations">
          <el-icon><Edit /></el-icon>
          <span>字段批注</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.hasPermission('agent.use')" index="/agent">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能体</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.hasPermission('agent.config')" index="/llm-settings">
          <el-icon><Tools /></el-icon>
          <span>模型配置</span>
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
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { House, User, Calendar, Clock, Tickets, DataAnalysis, Setting, UserFilled, Warning, Management, Fold, Expand, Document, DataBoard, Coin, Edit, ChatDotRound, Tools } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AgentLauncher from '@/components/AgentLauncher.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const showChangePwd = ref(false)
const changing = ref(false)
const pwdForm = ref({ oldPassword: '', newPassword: '' })

const isCollapsed = ref(false)
const sidebarWidth = computed(() => isCollapsed.value ? '64px' : '200px')
function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

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