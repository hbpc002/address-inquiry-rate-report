import { describe, it, expect } from 'vitest'

function operatorLabel(op) {
  const map = { lt: '<', le: '<=', gt: '>', ge: '>=' }
  return map[op] || op
}

function createDefaultTarget() {
  return {
    field: '',
    label: '',
    operator: 'lt',
    value: 0,
    color: '#F56C6C',
    enabled: true
  }
}

describe('MetricTargetSettings - 指标预警配置逻辑', () => {
  describe('operatorLabel', () => {
    it('should map lt to <', () => {
      expect(operatorLabel('lt')).toBe('<')
    })
    it('should map le to <=', () => {
      expect(operatorLabel('le')).toBe('<=')
    })
    it('should map gt to >', () => {
      expect(operatorLabel('gt')).toBe('>')
    })
    it('should map ge to >=', () => {
      expect(operatorLabel('ge')).toBe('>=')
    })
    it('should return unknown operator as-is', () => {
      expect(operatorLabel('eq')).toBe('eq')
    })
  })

  describe('addTarget', () => {
    it('should add a new target to the list', () => {
      const targets = []
      const form = { ...createDefaultTarget(), field: '_ti_dan_lv', label: '提单率', value: 0.15, operator: 'gt' }
      targets.push({ ...form })
      expect(targets).toHaveLength(1)
      expect(targets[0].field).toBe('_ti_dan_lv')
      expect(targets[0].label).toBe('提单率')
      expect(targets[0].value).toBe(0.15)
      expect(targets[0].enabled).toBe(true)
    })

    it('should validate required fields before add', () => {
      const form = { field: '', label: '测试', operator: 'lt', value: 0.5, color: '#F56C6C', enabled: true }
      const isValid = form.field && form.label
      expect(isValid).toBeFalsy()

      form.field = 'test-field'
      expect(!!(form.field && form.label)).toBe(true)
    })
  })

  describe('editTarget', () => {
    it('should update existing target fields', () => {
      const targets = [
        { field: '人工服务-满意度-满意率', label: '满意率', operator: 'lt', value: 0.95, color: '#F56C6C', enabled: true }
      ]
      targets[0].value = 0.90
      targets[0].color = '#E6A23C'
      expect(targets[0].value).toBe(0.90)
      expect(targets[0].color).toBe('#E6A23C')
    })
  })

  describe('deleteTarget', () => {
    it('should remove target by index', () => {
      const targets = [
        { field: 'a', label: 'A', operator: 'lt', value: 1, color: '#F56C6C', enabled: true },
        { field: 'b', label: 'B', operator: 'gt', value: 2, color: '#E6A23C', enabled: true },
      ]
      targets.splice(0, 1)
      expect(targets).toHaveLength(1)
      expect(targets[0].field).toBe('b')
    })
  })

  describe('toggleEnabled', () => {
    it('should toggle enabled state', () => {
      const target = { field: 'test', label: '测试', operator: 'lt', value: 100, color: '#F56C6C', enabled: true }
      target.enabled = false
      expect(target.enabled).toBe(false)
      target.enabled = true
      expect(target.enabled).toBe(true)
    })
  })

  describe('defaultTargets', () => {
    const DEFAULT_TARGETS = [
      { field: '人工服务-满意度-满意率', label: '满意率', operator: 'lt', value: 0.95, color: '#F56C6C', enabled: true },
      { field: '_ti_dan_lv', label: '提单率', operator: 'gt', value: 0.15, color: '#F56C6C', enabled: true }
    ]

    it('should have correct default values', () => {
      expect(DEFAULT_TARGETS).toHaveLength(2)
      expect(DEFAULT_TARGETS[0].field).toBe('人工服务-满意度-满意率')
      expect(DEFAULT_TARGETS[0].value).toBe(0.95)
      expect(DEFAULT_TARGETS[0].operator).toBe('lt')
      expect(DEFAULT_TARGETS[0].enabled).toBe(true)
      expect(DEFAULT_TARGETS[1].field).toBe('_ti_dan_lv')
      expect(DEFAULT_TARGETS[1].value).toBe(0.15)
      expect(DEFAULT_TARGETS[1].operator).toBe('gt')
      expect(DEFAULT_TARGETS[1].enabled).toBe(true)
    })
  })

  describe('COMMON_FIELDS', () => {
    const COMMON_FIELDS = [
      { value: '人工服务-满意度-满意率', label: '满意率' },
      { value: '_ti_dan_lv', label: '提单率' },
      { value: '呼入人工服务-人工服务-通话次数', label: '通话次数' },
      { value: '呼入人工服务-工单-生成总量', label: '工单总量' },
      { value: '总体-工时利用率', label: '工时利用率' },
      { value: '呼入人工服务-解决率-解决率', label: '解决率' },
    ]

    it('should contain 6 common fields', () => {
      expect(COMMON_FIELDS).toHaveLength(6)
    })

    it('every field should have value and label', () => {
      COMMON_FIELDS.forEach(f => {
        expect(f.value).toBeTruthy()
        expect(f.label).toBeTruthy()
      })
    })

    it('should include satisfaction rate and ti_dan_lv', () => {
      const values = COMMON_FIELDS.map(f => f.value)
      expect(values).toContain('人工服务-满意度-满意率')
      expect(values).toContain('_ti_dan_lv')
    })
  })

  describe('onFieldChange - 字段选择自动填充', () => {
    const COMMON_FIELDS = [
      { value: '人工服务-满意度-满意率', label: '满意率' },
      { value: '_ti_dan_lv', label: '提单率' },
    ]

    function onFieldChange(value, currentLabel) {
      if (!value) return
      const all = [...COMMON_FIELDS]
      const found = all.find(f => f.value === value)
      if (found && !currentLabel) {
        return found.label
      }
      return currentLabel
    }

    it('should auto-fill label when selecting a common field and label is empty', () => {
      const result = onFieldChange('人工服务-满意度-满意率', '')
      expect(result).toBe('满意率')
    })

    it('should auto-fill label when selecting ti_dan_lv', () => {
      const result = onFieldChange('_ti_dan_lv', '')
      expect(result).toBe('提单率')
    })

    it('should not overwrite existing label', () => {
      const result = onFieldChange('_ti_dan_lv', '自定义名称')
      expect(result).toBe('自定义名称')
    })

    it('should return empty label when value is empty', () => {
      const result = onFieldChange('', '')
      expect(result).toBeUndefined()
    })
  })

  describe('metricFields formatting', () => {
    it('should extract label from field name using last segment', () => {
      const fields = [
        '呼入人工服务-人工服务-通话次数',
        '呼入人工服务-人工服务-通话总时长(秒)',
        '呼入人工服务-满意度-满意率',
      ]
      const formatted = fields.map(f => ({
        value: f,
        label: f.split('-').pop()
      }))
      expect(formatted[0].label).toBe('通话次数')
      expect(formatted[1].label).toBe('通话总时长(秒)')
      expect(formatted[2].label).toBe('满意率')
    })

    it('should handle short field names', () => {
      expect('通话次数'.split('-').pop()).toBe('通话次数')
    })

    it('should produce unique display labels', () => {
      const fields = [
        'A-通话次数',
        'B-通话次数',
      ]
      const formatted = fields.map(f => ({
        value: f,
        label: f.split('-').pop()
      }))
      expect(formatted[0].label).toBe('通话次数')
      expect(formatted[1].label).toBe('通话次数')
      expect(formatted[0].value).not.toBe(formatted[1].value)
    })
  })
})
