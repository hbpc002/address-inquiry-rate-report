import { defineStore } from 'pinia'
import { api } from '@/stores/user'

const DEFAULTS = {
  enabled: true,
  label: '智能助手',
  icon_type: 'emoji',
  icon_value: '🤖',
  position: 'bottom-right',
  color: '#409EFF',
  draggable: true,
  pos_x: null,
  pos_y: null,
}

export const useLauncherStore = defineStore('launcher', {
  state: () => ({
    config: { ...DEFAULTS },
    pos: { left: null, top: null },
    loaded: false,
  }),
  actions: {
    async load() {
      try {
        const r = await api.get('/llm-providers/launcher')
        if (r.data) {
          this.config = { ...this.config, ...r.data }
          if (r.data.pos_x != null && r.data.pos_y != null) {
            this.pos = { left: r.data.pos_x, top: r.data.pos_y }
          }
        }
      } catch (e) {
        /* 使用默认配置 */
      } finally {
        this.loaded = true
      }
    },
    setConfig(partial) {
      this.config = { ...this.config, ...partial }
    },
    setPos(left, top) {
      this.pos = { left, top }
    },
  },
})
