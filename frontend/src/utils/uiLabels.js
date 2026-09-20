export const UI_LABEL_ITEMS = [
  { key: 'project_name', label: '项目主名称', placeholder: '客户服务中心运营管理平台', default: '客户服务中心运营管理平台' },
  { key: 'dashboard', label: '仪表盘（工效仪表盘）', default: '工效仪表盘' },
  { key: 'checkin_report', label: '签入签出报表（排班调度）', default: '排班调度' },
  { key: 'workload_report', label: '工作量报表（团队管理）', default: '团队管理' },
  { key: 'broadband_report', label: '宽带营销画像', default: '宽带营销画像' },
  { key: 'reports', label: '考勤报表', default: '考勤报表' },
  { key: 'menu_data', label: '菜单分组·数据管理', default: '数据管理' },
  { key: 'schedules', label: '排班管理', default: '排班管理' },
  { key: 'employees', label: '员工管理', default: '员工管理' },
  { key: 'checkins', label: '签到记录', default: '签到记录' },
  { key: 'training_records', label: '培训记录', default: '培训记录' },
  { key: 'workload', label: '工作量详单', default: '工作量详单' },
  { key: 'broadband_orders', label: '无缝订单', default: '无缝订单' },
  { key: 'menu_system', label: '菜单分组·系统设置', default: '系统设置' },
  { key: 'system', label: '系统管理', default: '系统管理' },
  { key: 'users', label: '用户管理', default: '用户管理' },
  { key: 'roles', label: '角色管理', default: '角色管理' },
  { key: 'work_hour_settings', label: '工时预警设置', default: '工时预警设置' },
  { key: 'salary_config', label: '绩效配置', default: '绩效配置' },
  { key: 'field_annotations', label: '字段批注', default: '字段批注' },
  { key: 'agent', label: '智能体（哟你通通）', default: '哟你通通' },
]

export const UI_LABEL_DEFAULTS = Object.fromEntries(UI_LABEL_ITEMS.map((item) => [item.key, item.default]))

export const UI_LABEL_KEYS = UI_LABEL_ITEMS.map((item) => item.key)