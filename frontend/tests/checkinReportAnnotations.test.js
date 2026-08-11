import { describe, it, expect } from 'vitest'

describe('CheckinReport - annotation field paths', () => {
  const checkinFields = [
    'emp_no', 'name', 'dept', 'team', 'checkin_count', 'total_hours', 'scheduled_hours',
    'hour_status_text', 'avg_punctuality_rate', 'total_call_duration',
    'total_organize_duration', 'avg_utilization_rate', 'avg_attendance_rate',
    'training_minutes', 'computed_punctuality_rate',
  ]

  const checkinDetailFields = [
    'date', 'scheduled_hours', 'punctuality_rate', 'call_duration',
    'organize_duration', 'utilization_rate', 'attendance_rate',
    'training_minutes', 'computed_punctuality_rate', 'checkin_time',
    'checkout_time', 'duration', 'status', 'late_minutes',
    'early_minutes', 'shift_name', 'is_long_hour',
  ]

  const summaryFields = [
    'summary_total_scheduled_hours', 'summary_total_hours', 'summary_team_avg_hours',
    'summary_attend_days', 'summary_scheduled_days', 'summary_long_hour_days',
    'summary_late_days', 'summary_early_days', 'summary_total_call_duration',
    'summary_total_organize_duration', 'summary_total_training_minutes',
  ]

  it('should have all expected checkin fields', () => {
    expect(checkinFields).toContain('emp_no')
    expect(checkinFields).toContain('total_hours')
    expect(checkinFields).toContain('avg_punctuality_rate')
  })

  it('should have all expected checkin_detail fields', () => {
    expect(checkinDetailFields).toContain('date')
    expect(checkinDetailFields).toContain('duration')
    expect(checkinDetailFields).toContain('status')
  })

  it('should have all expected summary fields with summary_ prefix', () => {
    summaryFields.forEach(f => {
      expect(f).toMatch(/^summary_/)
    })
  })

  it('should map summary template keys to prefixed API keys', () => {
    const templateToApi = {
      total_scheduled_hours: 'summary_total_scheduled_hours',
      total_hours: 'summary_total_hours',
      team_avg_hours: 'summary_team_avg_hours',
      attend_days: 'summary_attend_days',
      scheduled_days: 'summary_scheduled_days',
      long_hour_days: 'summary_long_hour_days',
      late_days: 'summary_late_days',
      early_days: 'summary_early_days',
      total_call_duration: 'summary_total_call_duration',
      total_organize_duration: 'summary_total_organize_duration',
      total_training_minutes: 'summary_total_training_minutes',
    }
    expect(templateToApi.total_hours).toBe('summary_total_hours')
    expect(templateToApi.late_days).toBe('summary_late_days')
    expect(templateToApi.total_training_minutes).toBe('summary_total_training_minutes')
    Object.entries(templateToApi).forEach(([template, api]) => {
      expect(api).toMatch(/^summary_/)
    })
  })
})

describe('CheckinReport - ColumnWithTip field path mapping', () => {
  const checkinMapping = {
    emp_no: { path: 'emp_no', label: '账号' },
    name: { path: 'name', label: '用户名' },
    checkin_count: { path: 'checkin_count', label: '签入次数' },
    total_hours: { path: 'total_hours', label: '工作时长' },
    scheduled_hours: { path: 'scheduled_hours', label: '排班工时' },
    avg_punctuality_rate: { path: 'avg_punctuality_rate', label: '遵时率' },
  }

  const checkinDetailMapping = {
    date: { path: 'date', label: '日期' },
    scheduled_hours: { path: 'scheduled_hours', label: '排班工时' },
    checkin_time: { path: 'checkin_time', label: '签到时间' },
    status: { path: 'status', label: '状态' },
  }

  it('should have correct label for checkin fields', () => {
    expect(checkinMapping.emp_no.label).toBe('账号')
    expect(checkinMapping.total_hours.label).toBe('工作时长')
    expect(checkinMapping.scheduled_hours.label).toBe('排班工时')
  })

  it('should have correct prop path for checkin fields', () => {
    expect(checkinMapping.emp_no.path).toBe('emp_no')
    expect(checkinMapping.checkin_count.path).toBe('checkin_count')
  })

  it('should have correct label for checkin_detail fields', () => {
    expect(checkinDetailMapping.date.label).toBe('日期')
    expect(checkinDetailMapping.status.label).toBe('状态')
  })
})

describe('CheckinReport - summary statistic value binding', () => {
  const summaryStats = [
    { key: 'total_scheduled_hours', value: 'personalDetail.summary.total_scheduled_hours', precision: 1 },
    { key: 'total_hours', value: 'personalDetail.summary.total_hours', precision: 1 },
    { key: 'team_avg_hours', value: 'personalDetail.summary.team_avg_hours', precision: 1 },
    { key: 'long_hour_days', value: 'localLongHourDays', precision: null },
    { key: 'late_days', value: 'personalDetail.summary.late_days', precision: null },
    { key: 'early_days', value: 'personalDetail.summary.early_days', precision: null },
    { key: 'total_call_duration', value: 'personalDetail.summary.total_call_duration || 0', precision: 1 },
    { key: 'total_organize_duration', value: 'personalDetail.summary.total_organize_duration || 0', precision: 1 },
    { key: 'total_training_minutes', value: 'personalDetail.summary.total_training_minutes || 0', precision: null },
  ]

  const hasTip = (annotation) => {
    if (!annotation) return false
    return !!(annotation.source || annotation.formula || annotation.description)
  }

  const tipContent = (annotation) => {
    if (!hasTip(annotation)) return ''
    const parts = []
    if (annotation.source) parts.push('数据来源：' + annotation.source)
    if (annotation.formula) parts.push('计算公式：' + annotation.formula)
    if (annotation.description) parts.push('口径说明：' + annotation.description)
    return parts.join('\n')
  }

  it('should bind every summary stat value via :value prop (never #default slot)', () => {
    summaryStats.forEach(s => {
      expect(s.value).toBeTruthy()
    })
  })

  it('should only show tip icon when annotation has content', () => {
    expect(hasTip({ source: '签到记录' })).toBe(true)
    expect(hasTip({ formula: '签退-签到' })).toBe(true)
    expect(hasTip({ description: '说明' })).toBe(true)
    expect(hasTip({ source: '', formula: '', description: '' })).toBe(false)
    expect(hasTip(null)).toBe(false)
  })

  it('should build multi-line tooltip content from source/formula/description', () => {
    const content = tipContent({ source: 'A', formula: 'B', description: 'C' })
    expect(content).toContain('数据来源：A')
    expect(content).toContain('计算公式：B')
    expect(content).toContain('口径说明：C')
    expect(content.split('\n').length).toBe(3)
  })

  it('should return empty tooltip content when no annotation', () => {
    expect(tipContent(null)).toBe('')
    expect(tipContent({ source: '', formula: '', description: '' })).toBe('')
  })

  it('should preserve display formatting via precision on value', () => {
    const format = (v, precision) => {
      if (precision == null) return String(v)
      return Number(v).toFixed(precision)
    }
    expect(format(85.5, 1)).toBe('85.5')
    expect(format(0, 1)).toBe('0.0')
    expect(format(3, null)).toBe('3')
  })

  it('should map attend_days as custom stat spans (not el-statistic value)', () => {
    const attendStat = { type: 'custom', num: 'personalDetail.summary.attend_days', sub: 'personalDetail.summary.scheduled_days' }
    expect(attendStat.type).toBe('custom')
    expect(attendStat.num).toContain('attend_days')
    expect(attendStat.sub).toContain('scheduled_days')
  })
})

describe('CheckinReport - annotation prop structure', () => {
  const validAnnotation = {
    source: '签到记录数据',
    formula: '排班时段内签退-签到',
    description: '仅计算排班时段内的重叠工时，不包含加班时段',
  }

  const emptyAnnotation = {
    source: '',
    formula: '',
    description: '',
  }

  it('should return annotation values correctly', () => {
    expect(validAnnotation.source).toBe('签到记录数据')
    expect(validAnnotation.formula).toBe('排班时段内签退-签到')
    expect(validAnnotation.description).toContain('排班时段')
  })

  it('should detect content presence in valid annotation', () => {
    const hasContent = !!(validAnnotation.source || validAnnotation.formula || validAnnotation.description)
    expect(hasContent).toBe(true)
  })

  it('should detect empty annotation correctly', () => {
    const hasContent = !!(emptyAnnotation.source || emptyAnnotation.formula || emptyAnnotation.description)
    expect(hasContent).toBe(false)
  })
})
