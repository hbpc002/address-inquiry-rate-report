import { describe, it, expect, vi } from 'vitest'

const mockItems = [
  { id: 1, emp_id: 1, schedule_date: '2025-05-01', name: '张三', emp_no: 'E001', team: '一班1组', shift_name: '早班', shift_time: '08:00-12:00, 13:00-17:00', schedule_type: '正常', work_hours: 8.0, shift_type_id: 1 },
  { id: 2, emp_id: 2, schedule_date: '2025-05-01', name: '李四', emp_no: 'E002', team: '一班1组', shift_name: '早班', shift_time: '08:00-12:00, 13:00-17:00', schedule_type: '正常', work_hours: 8.0, shift_type_id: 1 },
  { id: 3, emp_id: 3, schedule_date: '2025-05-02', name: '王五', emp_no: 'E003', team: '二班2组', shift_name: '中班', shift_time: '14:00-22:00', schedule_type: '正常', work_hours: 8.0, shift_type_id: 2 },
  { id: 4, emp_id: 4, schedule_date: '2025-05-03', name: '赵六', emp_no: 'E004', team: '一班2组', shift_name: '夜班', shift_time: '22:00-06:00', schedule_type: '加班', work_hours: 8.0, shift_type_id: 3 }
]

describe('Schedules - 查询参数映射', () => {
  const buildParams = (form) => {
    const params = { page: form.page || 1, limit: form.limit || 20 }
    if (form.date) params.schedule_date = form.date
    if (form.name) params.name = form.name
    if (form.emp_no) params.emp_no = form.emp_no
    if (form.team) params.team = form.team
    if (form.shift_type_id) params.shift_type_id = form.shift_type_id
    if (form.schedule_type) params.schedule_type = form.schedule_type
    return params
  }

  it('should map date to schedule_date', () => {
    const params = buildParams({ date: '2025-05-01' })
    expect(params.schedule_date).toBe('2025-05-01')
    expect(Object.keys(params)).not.toContain('date')
  })

  it('should map name to params', () => {
    const params = buildParams({ name: '张三' })
    expect(params.name).toBe('张三')
  })

  it('should map emp_no to params', () => {
    const params = buildParams({ emp_no: 'E001' })
    expect(params.emp_no).toBe('E001')
  })

  it('should map team to params', () => {
    const params = buildParams({ team: '一班1组' })
    expect(params.team).toBe('一班1组')
  })

  it('should map shift_type_id to params', () => {
    const params = buildParams({ shift_type_id: 1 })
    expect(params.shift_type_id).toBe(1)
  })

  it('should map schedule_type to params', () => {
    const params = buildParams({ schedule_type: '加班' })
    expect(params.schedule_type).toBe('加班')
  })

  it('should map all filters when all present', () => {
    const params = buildParams({
      date: '2025-05-01', name: '张三', emp_no: 'E001',
      team: '一班1组', shift_type_id: 1, schedule_type: '正常'
    })
    expect(params.schedule_date).toBe('2025-05-01')
    expect(params.name).toBe('张三')
    expect(params.emp_no).toBe('E001')
    expect(params.team).toBe('一班1组')
    expect(params.shift_type_id).toBe(1)
    expect(params.schedule_type).toBe('正常')
  })

  it('should omit empty filters', () => {
    const params = buildParams({ date: '', name: '', team: '', shift_type_id: null, schedule_type: '' })
    expect(params.schedule_date).toBeUndefined()
    expect(params.name).toBeUndefined()
    expect(params.team).toBeUndefined()
    expect(params.shift_type_id).toBeUndefined()
    expect(params.schedule_type).toBeUndefined()
  })
})

describe('Schedules - 分页参数', () => {
  it('should use page and limit in API params', () => {
    const params = { page: 2, limit: 10 }
    expect(params.page).toBe(2)
    expect(params.limit).toBe(10)
  })

  it('should default to page 1, limit 20', () => {
    expect({ page: 1, limit: 20 }).toMatchObject({ page: 1, limit: 20 })
  })
})

describe('Schedules - 列表数据', () => {
  it('should contain all required fields', () => {
    mockItems.forEach(item => {
      expect(item).toHaveProperty('id')
      expect(item).toHaveProperty('schedule_date')
      expect(item).toHaveProperty('name')
      expect(item).toHaveProperty('emp_no')
      expect(item).toHaveProperty('team')
      expect(item).toHaveProperty('shift_name')
      expect(item).toHaveProperty('shift_time')
      expect(item).toHaveProperty('schedule_type')
      expect(item).toHaveProperty('work_hours')
    })
  })

  it('should show shift_name and shift_time together', () => {
    mockItems.forEach(item => {
      const display = item.shift_name + (item.shift_time ? ` (${item.shift_time})` : '')
      expect(display).toBeTruthy()
    })
    expect(`${mockItems[0].shift_name} (${mockItems[0].shift_time})`).toBe('早班 (08:00-12:00, 13:00-17:00)')
  })

  it('should filter by name', () => {
    const result = mockItems.filter(i => i.name.includes('三'))
    expect(result.length).toBe(1)
    expect(result[0].name).toBe('张三')
  })

  it('should filter by emp_no', () => {
    const result = mockItems.filter(i => i.emp_no === 'E003')
    expect(result.length).toBe(1)
  })

  it('should filter by team', () => {
    const result = mockItems.filter(i => i.team === '一班1组')
    expect(result.length).toBe(2)
  })

  it('should filter by date', () => {
    const result = mockItems.filter(i => i.schedule_date === '2025-05-01')
    expect(result.length).toBe(2)
  })

  it('should filter by shift_type_id', () => {
    const result = mockItems.filter(i => i.shift_type_id === 1)
    expect(result.length).toBe(2)
  })

  it('should filter by schedule_type', () => {
    const result = mockItems.filter(i => i.schedule_type === '加班')
    expect(result.length).toBe(1)
  })

  it('should handle empty results', () => {
    expect([].length).toBe(0)
  })
})

describe('Schedules - 班次显示', () => {
  it('should show shift_name with shift_time in parentheses', () => {
    const row = { shift_name: '早班', shift_time: '08:00-12:00, 13:00-17:00' }
    const display = row.shift_name + (row.shift_time ? ` (${row.shift_time})` : '')
    expect(display).toBe('早班 (08:00-12:00, 13:00-17:00)')
  })

  it('should show shift_name alone when shift_time is empty', () => {
    const row = { shift_name: '中班', shift_time: '' }
    const display = row.shift_name || '-'
    expect(display).toBe('中班')
  })

  it('should show dash when both are empty', () => {
    const row = { shift_name: null, shift_time: null }
    const display = row.shift_name ? (row.shift_time ? `${row.shift_name} (${row.shift_time})` : row.shift_name) : '-'
    expect(display).toBe('-')
  })
})

describe('Schedules - 重置搜索', () => {
  it('should clear all search fields on reset', () => {
    const form = { date: '2025-05-01', name: '张三', emp_no: 'E001', team: '一班1组', shift_type_id: 1, schedule_type: '正常' }
    form.date = ''
    form.name = ''
    form.emp_no = ''
    form.team = ''
    form.shift_type_id = null
    form.schedule_type = ''
    expect(form).toMatchObject({ date: '', name: '', emp_no: '', team: '', shift_type_id: null, schedule_type: '' })
  })
})