import { describe, it, expect } from 'vitest'
import { UI_LABEL_ITEMS, UI_LABEL_DEFAULTS, UI_LABEL_KEYS } from '@/utils/uiLabels'

const EXPECTED = [
  ['project_name', '客户服务中心运营管理平台'],
  ['dashboard', '工效仪表盘'],
  ['checkin_report', '排班调度'],
  ['workload_report', '团队管理'],
  ['broadband_report', '宽带营销画像'],
  ['reports', '考勤报表'],
  ['menu_data', '数据管理'],
  ['schedules', '排班管理'],
  ['employees', '员工管理'],
  ['checkins', '签到记录'],
  ['training_records', '培训记录'],
  ['workload', '工作量详单'],
  ['broadband_orders', '无缝订单'],
  ['menu_system', '系统设置'],
  ['system', '系统管理'],
  ['users', '用户管理'],
  ['roles', '角色管理'],
  ['work_hour_settings', '工时预警设置'],
  ['salary_config', '绩效配置'],
  ['field_annotations', '字段批注'],
  ['agent', '哟你通通'],
]

describe('uiLabels 元数据清单', () => {
  it('包含全部 21 个菜单可配置项', () => {
    expect(UI_LABEL_ITEMS.map((item) => item.key)).toEqual(EXPECTED.map(([key]) => key))
  })

  it('每个菜单项默认值非空且有表单说明', () => {
    for (const item of UI_LABEL_ITEMS) {
      expect(item.key.length).toBeGreaterThan(0)
      expect(item.label.length).toBeGreaterThan(0)
      expect(String(item.default).trim().length).toBeGreaterThan(0)
    }
  })

  it('键唯一', () => {
    const keys = UI_LABEL_ITEMS.map((item) => item.key)
    expect(new Set(keys).size).toBe(keys.length)
  })

  it('默认值与菜单现状一致', () => {
    for (const [key, value] of EXPECTED) {
      expect(UI_LABEL_DEFAULTS[key]).toBe(value)
    }
  })

  it('UI_LABEL_DEFAULTS / UI_LABEL_KEYS 与 UI_LABEL_ITEMS 一致', () => {
    expect(Object.keys(UI_LABEL_DEFAULTS)).toEqual(UI_LABEL_KEYS)
    expect(UI_LABEL_KEYS).toEqual(EXPECTED.map(([key]) => key))
  })
})