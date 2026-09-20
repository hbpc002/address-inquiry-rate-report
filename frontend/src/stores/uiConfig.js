import { defineStore } from 'pinia'
import { api } from '@/stores/user'
import { UI_LABEL_DEFAULTS } from '@/utils/uiLabels'

const DEFAULTS = { ...UI_LABEL_DEFAULTS }

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