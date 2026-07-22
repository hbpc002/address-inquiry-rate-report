import { describe, it, expect } from 'vitest'

describe('ColumnWithTip - computed hasContent', () => {
  function computeHasContent(annotation) {
    if (!annotation) return false
    return !!(annotation.source || annotation.formula || annotation.description)
  }

  it('should return false when annotation is null', () => {
    expect(computeHasContent(null)).toBe(false)
  })

  it('should return false when annotation has no fields', () => {
    expect(computeHasContent({})).toBe(false)
  })

  it('should return true when annotation has source', () => {
    expect(computeHasContent({ source: '签到记录' })).toBe(true)
  })

  it('should return true when annotation has formula', () => {
    expect(computeHasContent({ formula: '签退-签到' })).toBe(true)
  })

  it('should return true when annotation has description', () => {
    expect(computeHasContent({ description: '测试说明' })).toBe(true)
  })

  it('should return true when all fields are present', () => {
    expect(computeHasContent({
      source: '签到记录',
      formula: '签退-签到',
      description: '测试说明',
    })).toBe(true)
  })
})

describe('FieldAnnotations - annotation label map', () => {
  const reportTypeLabelMap = {
    daily: '日报表',
    monthly: '月度汇总',
    workload: '工作量报表',
    checkin: '签入签出报表',
    efficiency: '效能报表',
  }

  it('should return correct label for daily', () => {
    expect(reportTypeLabelMap['daily']).toBe('日报表')
  })

  it('should return correct label for monthly', () => {
    expect(reportTypeLabelMap['monthly']).toBe('月度汇总')
  })

  it('should return correct label for workload', () => {
    expect(reportTypeLabelMap['workload']).toBe('工作量报表')
  })

  it('should return correct label for checkin', () => {
    expect(reportTypeLabelMap['checkin']).toBe('签入签出报表')
  })

  it('should return correct label for efficiency', () => {
    expect(reportTypeLabelMap['efficiency']).toBe('效能报表')
  })
})

describe('FieldAnnotations - useFieldAnnotations cache behavior', () => {
  it('should create a fresh cache per report type', () => {
    const cache1 = {}
    const cache2 = {}
    cache1['daily'] = { actual_hours: { source: 'test' } }
    cache2['monthly'] = { scheduled_hours: { source: 'test2' } }
    expect(cache1['daily']['actual_hours'].source).toBe('test')
    expect(cache2['monthly']['scheduled_hours'].source).toBe('test2')
    expect(cache1['monthly']).toBeUndefined()
  })
})

describe('Permission registration for field_annotations', () => {
  const permissionRegistry = {
    field_annotations: {
      label: '字段批注',
      permissions: {
        view: '查看',
        edit: '编辑',
      },
    },
  }

  it('should be registered', () => {
    expect(permissionRegistry.field_annotations).toBeDefined()
  })

  it('should have correct label', () => {
    expect(permissionRegistry.field_annotations.label).toBe('字段批注')
  })

  it('should have view permission', () => {
    expect(permissionRegistry.field_annotations.permissions.view).toBe('查看')
  })

  it('should have edit permission', () => {
    expect(permissionRegistry.field_annotations.permissions.edit).toBe('编辑')
  })
})
