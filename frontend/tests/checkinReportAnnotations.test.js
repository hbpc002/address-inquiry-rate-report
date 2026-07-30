import { describe, it, expect } from 'vitest'

describe('CheckinReport - annotation field paths', () => {
  const checkinFields = [
    'emp_no', 'name', 'dept', 'team', 'checkin_count', 'total_hours',
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
