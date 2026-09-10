import { defineStore } from 'pinia'
import { api } from '@/stores/user'

const DEFAULTS = {
  project_name: '客户服务中心运营管理平台',
  dashboard: '工效仪表盘',
  checkin_report: '排班调度',
  workload_report: '团队管理',
  agent: '哟你通通',
}

export const useUiConfigStore = defineStore('uiConfig', {
  state: () => ({
    labels: { ...DEFAULTS },
    loaded: false,
  }),
  actions: {
    async load() {
      try {
        const r = await api.get('/ui-labels')
        if (r.data) {
          this.labels = { ...this.labels, ...r.data }
        }
      } catch (e) {
        /* 使用默认名称 */
      } finally {
        this.loaded = true
        this.applyTitle()
      }
    },
    setLabels(partial) {
      this.labels = { ...this.labels, ...partial }
      this.applyTitle()
    },
    async update(patch) {
      const r = await api.put('/ui-labels', patch)
      if (r.data) {
        this.labels = { ...this.labels, ...r.data }
        this.applyTitle()
      }
      return r.data
    },
    applyTitle() {
      document.title = this.labels.project_name || DEFAULTS.project_name
    },
  },
})