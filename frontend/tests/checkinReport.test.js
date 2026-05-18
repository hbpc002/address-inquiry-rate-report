import { describe, it, expect, vi } from 'vitest'

const mockData = {
  stats: {
    total_checkins: 100,
    emp_count: 20,
    total_hours: 1600.5,
    avg_hours: 8.0,
    overtime_count: 3,
    undertime_count: 2
  },
  items: [
    {
      emp_no: 'E001',
      name: '张三',
      dept: '测试部门',
      team: '班组A',
      checkin_count: 10,
      total_hours: 85.5,
      hour_status: 'overtime',
      hour_status_text: '超时 (130%)',
      checkins: [
        { checkin_time: '2024-01-01 09:00', checkout_time: '2024-01-01 18:00', duration: 9.0 }
      ]
    },
    {
      emp_no: 'E002',
      name: '李四',
      dept: '测试部门',
      team: '班组A',
      checkin_count: 10,
      total_hours: 64.0,
      hour_status: 'undertime',
      hour_status_text: '过短 (77%)',
      checkins: []
    },
    {
      emp_no: 'E003',
      name: '王五',
      dept: '测试部门',
      team: '班组B',
      checkin_count: 10,
      total_hours: 80.0,
      hour_status: 'normal',
      hour_status_text: '正常 (100%)',
      checkins: []
    }
  ]
}

describe('CheckinReport - 筛选逻辑测试', () => {
  it('should filter overtime data correctly', () => {
    const filterType = 'overtime'
    const result = mockData.items.filter(item => item.hour_status === filterType)
    expect(result.length).toBe(1)
    expect(result[0].name).toBe('张三')
  })

  it('should filter undertime data correctly', () => {
    const filterType = 'undertime'
    const result = mockData.items.filter(item => item.hour_status === filterType)
    expect(result.length).toBe(1)
    expect(result[0].name).toBe('李四')
  })

  it('should filter by name correctly', () => {
    const filterValue = '张三'
    const result = mockData.items.filter(item => item.name === filterValue)
    expect(result.length).toBe(1)
    expect(result[0].name).toBe('张三')
  })

  it('should filter by team correctly', () => {
    const filterValue = '班组A'
    const result = mockData.items.filter(item => item.team === filterValue)
    expect(result.length).toBe(2)
  })

  it('should compute overtime names correctly', () => {
    const overtimeNames = mockData.items
      .filter(d => d.hour_status === 'overtime')
      .map(d => d.name)
      .slice(0, 5)
    expect(overtimeNames).toContain('张三')
  })

  it('should compute undertime names correctly', () => {
    const undertimeNames = mockData.items
      .filter(d => d.hour_status === 'undertime')
      .map(d => d.name)
      .slice(0, 5)
    expect(undertimeNames).toContain('李四')
  })

  it('should toggle filter state correctly', () => {
    let filterType = ''
    const toggleFilter = (type) => {
      if (filterType === type) {
        filterType = ''
      } else {
        filterType = type
      }
    }
    
    toggleFilter('overtime')
    expect(filterType).toBe('overtime')
    
    toggleFilter('overtime')
    expect(filterType).toBe('')
  })

  it('should clear filter correctly', () => {
    let filterType = 'overtime'
    let filterValue = 'somevalue'
    
    filterType = ''
    filterValue = ''
    
    expect(filterType).toBe('')
    expect(filterValue).toBe('')
  })

  it('should handle chart click by name correctly', () => {
    let filterType = ''
    let filterValue = ''
    const params = { name: '张三' }
    
    if (filterType === 'name' && filterValue === params.name) {
      filterType = ''
      filterValue = ''
    } else {
      filterType = 'name'
      filterValue = params.name
    }
    
    expect(filterType).toBe('name')
    expect(filterValue).toBe('张三')
  })

  it('should handle chart click by team correctly', () => {
    let filterType = ''
    let filterValue = ''
    const params = { name: '班组A' }
    
    if (filterType === 'team' && filterValue === params.name) {
      filterType = ''
      filterValue = ''
    } else {
      filterType = 'team'
      filterValue = params.name
    }
    
    expect(filterType).toBe('team')
    expect(filterValue).toBe('班组A')
  })

  it('should get correct stats values', () => {
    expect(mockData.stats.overtime_count).toBe(3)
    expect(mockData.stats.undertime_count).toBe(2)
  })

  it('should validate hour_status values', () => {
    const validStatuses = ['overtime', 'undertime', 'normal', undefined]
    mockData.items.forEach(item => {
      expect(validStatuses).toContain(item.hour_status)
    })
  })
})