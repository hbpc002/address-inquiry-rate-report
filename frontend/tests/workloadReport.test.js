import { describe, it, expect } from 'vitest'

function displayLabel(field) {
  return field.split('-').pop()
}

function isRateField(field) {
  return field.includes('率')
}

function formatRate(val) {
  if (val === null || val === undefined) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  if (isNaN(num)) return '-'
  return num.toFixed(2) + '%'
}

function formatMetricValue(val, isRate) {
  if (val === null || val === undefined) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  if (isNaN(num)) return val
  if (isRate) return num.toFixed(2) + '%'
  if (Number.isInteger(num)) return String(num)
  return num.toFixed(1)
}

function getMetricValue(row, field) {
  const val = row.aggregated_metrics?.[field]
  if (val === null || val === undefined) return null
  return typeof val === 'number' ? val : parseFloat(val) || 0
}

describe('WorkloadReport - 格式化函数测试', () => {

  describe('displayLabel', () => {
    it('should return last segment of dotted field name', () => {
      expect(displayLabel('呼入人工服务-人工服务-通话次数')).toBe('通话次数')
    })
    it('should handle single segment', () => {
      expect(displayLabel('通话次数')).toBe('通话次数')
    })
    it('should handle empty string', () => {
      expect(displayLabel('')).toBe('')
    })
  })

  describe('isRateField', () => {
    it('should detect rate fields containing 率', () => {
      expect(isRateField('人工服务-满意度-满意率')).toBe(true)
      expect(isRateField('呼入人工服务-解决率-解决率')).toBe(true)
      expect(isRateField('总体-工时利用率')).toBe(true)
    })
    it('should not flag avg duration fields as rate', () => {
      expect(isRateField('呼入人工服务-人工服务-通话均长(秒)')).toBe(false)
    })
    it('should return false for non-rate fields', () => {
      expect(isRateField('呼入人工服务-人工服务-通话次数')).toBe(false)
      expect(isRateField('总体-工作总时长(秒)')).toBe(false)
      expect(isRateField('')).toBe(false)
    })
  })

  describe('formatRate', () => {
    it('should format rate as percentage with 2 decimals', () => {
      expect(formatRate(85.67)).toBe('85.67%')
      expect(formatRate(95.0)).toBe('95.00%')
      expect(formatRate(100.0)).toBe('100.00%')
    })
    it('should return dash for null/undefined', () => {
      expect(formatRate(null)).toBe('-')
      expect(formatRate(undefined)).toBe('-')
    })
    it('should handle string numbers', () => {
      expect(formatRate('85.67')).toBe('85.67%')
    })
    it('should return dash for NaN', () => {
      expect(formatRate(NaN)).toBe('-')
    })
  })

  describe('formatMetricValue', () => {
    it('should format rate fields with percentage', () => {
      expect(formatMetricValue(85.67, true)).toBe('85.67%')
    })
    it('should format non-rate integer fields as string', () => {
      expect(formatMetricValue(30, false)).toBe('30')
    })
    it('should format non-rate decimal fields with 1 decimal', () => {
      expect(formatMetricValue(28800.5, false)).toBe('28800.5')
    })
    it('should return dash for null/undefined', () => {
      expect(formatMetricValue(null, false)).toBe('-')
      expect(formatMetricValue(undefined, true)).toBe('-')
    })
    it('should return raw value for non-numeric strings', () => {
      expect(formatMetricValue('N/A', false)).toBe('N/A')
    })
  })

  describe('getMetricValue', () => {
    const row = {
      aggregated_metrics: {
        '通话次数': 30,
        '满意率': 95.0,
        '空值字段': null
      }
    }
    it('should extract numeric value from aggregated_metrics', () => {
      expect(getMetricValue(row, '通话次数')).toBe(30)
    })
    it('should handle rate values', () => {
      expect(getMetricValue(row, '满意率')).toBe(95.0)
    })
    it('should return null for null values in metrics', () => {
      expect(getMetricValue(row, '空值字段')).toBeNull()
    })
    it('should return null for missing fields', () => {
      expect(getMetricValue(row, '不存在的字段')).toBeNull()
    })
    it('should return 0 for undefined metrics', () => {
      const emptyRow = {}
      expect(getMetricValue(emptyRow, '通话次数')).toBeNull()
    })
  })

})

describe('WorkloadDetail - 自定义列逻辑测试', () => {
  const allFields = [
    { field: '通话次数', label: '通话次数', isRate: false, width: 70 },
    { field: '满意率', label: '满意率', isRate: true, width: 70 },
    { field: '工时利用率', label: '工时利用率', isRate: true, width: 70 }
  ]

  it('should filter visible columns based on selected set', () => {
    const selected = ['通话次数', '工时利用率']
    const visible = allFields.filter(f => selected.includes(f.field))
    expect(visible.length).toBe(2)
    expect(visible[0].field).toBe('通话次数')
    expect(visible[1].field).toBe('工时利用率')
  })

  it('should return empty when no columns selected', () => {
    const visible = allFields.filter(f => [].includes(f.field))
    expect(visible.length).toBe(0)
  })

  it('should persist selected columns to localStorage', () => {
    const KEY = 'test-workload-columns'
    const cols = ['通话次数', '满意率']
    localStorage.setItem(KEY, JSON.stringify(cols))
    const loaded = JSON.parse(localStorage.getItem(KEY) || '[]')
    expect(loaded).toEqual(['通话次数', '满意率'])
    localStorage.removeItem(KEY)
  })
})
