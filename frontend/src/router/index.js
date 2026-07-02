import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/',
    name: 'Main',
    component: () => import('../views/Main.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue')
      },
      {
        path: 'employees',
        name: 'Employees',
        component: () => import('../views/Employees.vue'),
        meta: { permission: 'employees.view' }
      },
      {
        path: 'schedules',
        name: 'Schedules',
        component: () => import('../views/Schedules.vue'),
        meta: { permission: 'schedules.view' }
      },
      {
        path: 'checkins',
        name: 'Checkins',
        component: () => import('../views/Checkins.vue'),
        meta: { permission: 'checkins.view' }
      },
      {
        path: 'checkin-report',
        name: 'CheckinReport',
        component: () => import('../views/CheckinReport.vue'),
        meta: { permission: 'checkin_report.view' }
      },
      {
        path: 'workloads',
        name: 'Workloads',
        component: () => import('../views/Workloads.vue'),
        meta: { permission: 'workload.view' }
      },
      {
        path: 'workload-report',
        name: 'WorkloadReport',
        component: () => import('../views/WorkloadReport.vue'),
        meta: { permission: 'workload_report.view' }
      },
      {
        path: 'work-hour-settings',
        name: 'WorkHourSettings',
        component: () => import('../views/WorkHourSettings.vue'),
        meta: { permission: 'work_hour_settings.view' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('../views/Reports.vue'),
        meta: { permission: 'reports.view' }
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('../views/System.vue'),
        meta: { permission: 'system.view' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/Users.vue'),
        meta: { permission: 'users.view' }
      },
      {
        path: 'roles',
        name: 'Roles',
        component: () => import('../views/Roles.vue'),
        meta: { permission: 'roles.view' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (to.path !== '/login' && !userStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } else if (to.meta.permission && !userStore.hasPermission(to.meta.permission)) {
    next('/')
  } else {
    next()
  }
})

export default router