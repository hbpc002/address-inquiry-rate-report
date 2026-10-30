<template>
  <div class="no-permission">
    <el-card class="no-permission-card">
      <h2>暂无访问权限</h2>
      <p>当前账号没有可访问的功能，请联系管理员分配角色权限。</p>
      <el-button type="primary" @click="handleLogout">退出登录</el-button>
    </el-card>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

function handleLogout() {
  userStore.logout()
  router.replace('/login')
}
</script>

<style scoped>
.no-permission {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.no-permission-card {
  width: 420px;
  text-align: center;
}

.no-permission-card h2 {
  margin-bottom: 16px;
  color: #303133;
}

.no-permission-card p {
  margin-bottom: 24px;
  color: #606266;
}
</style>
