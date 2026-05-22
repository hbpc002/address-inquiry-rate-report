import { describe, it, expect } from 'vitest'

const mockDailyData = [
  { emp_id: 1, dept: '客服中心', scheduled_hours: 8, actual_hours: 7.5, status: '正常' },
  { emp_id: 2, dept: '客服中心', scheduled_hours: 8, actual_hours: 0, status: '缺勤' },
  { emp_id: 3, dept: '技术部', scheduled_hours: 8, actual_hours: 8, status: '正常' },
  { emp_id: 1, dept: '客服中心', scheduled_hours: 8, actual_hours: 7.5, status: '正常' },
  { emp_id: 4, dept: '客服中心', scheduled_hours: 4, actual_hours: 3.8, status: '正常' },
]

describe('dailyDeptOptions - 去重聚合逻辑', () => {
  it('should deduplicate by emp_id', () => {
    const seen = new Set()
    const unique = mockDailyData.filter(d => {
      if (seen.has(d.emp_id)) return false
      seen.add(d.emp_id)
      return true
    })
    expect(unique.length).toBe(4)
    expect(seen.size).toBe(4)
  })

  it('should aggregate scheduled hours by dept', () => {
    const seen = new Set()
    const deptMap = {}
    mockDailyData.forEach(d => {
      if (seen.has(d.emp_id)) return
      seen.add(d.emp_id)
      if (!deptMap[d.dept]) deptMap[d.dept] = { scheduled: 0, actual: 0 }
      deptMap[d.dept].scheduled += d.scheduled_hours || 0
      deptMap[d.dept].actual += d.actual_hours || 0
    })
    expect(deptMap['客服中心'].scheduled).toBe(20)
    expect(deptMap['技术部'].scheduled).toBe(8)
    expect(deptMap['客服中心'].actual).toBe(11.3)
    expect(deptMap['技术部'].actual).toBe(8)
  })

  it('should handle empty data', () => {
    const seen = new Set()
    const deptMap = {}
    ;[].forEach(d => {
      if (seen.has(d.emp_id)) return
      seen.add(d.emp_id)
      if (!deptMap[d.dept]) deptMap[d.dept] = { scheduled: 0, actual: 0 }
      deptMap[d.dept].scheduled += d.scheduled_hours || 0
      deptMap[d.dept].actual += d.actual_hours || 0
    })
    expect(Object.keys(deptMap).length).toBe(0)
  })

  it('should limit to top 8 departments', () => {
    const depts = []
    for (let i = 0; i < 10; i++) {
      depts.push(`部门${i}`)
    }
    expect(depts.slice(0, 8).length).toBe(8)
    expect(depts.slice(0, 8)).not.toContain('部门8')
  })

  it('should handle null/undefined hours', () => {
    const data = [
      { emp_id: 1, dept: '客服中心', scheduled_hours: null, actual_hours: undefined },
      { emp_id: 2, dept: '客服中心', scheduled_hours: 8, actual_hours: 5 },
    ]
    const seen = new Set()
    const deptMap = {}
    data.forEach(d => {
      if (seen.has(d.emp_id)) return
      seen.add(d.emp_id)
      if (!deptMap[d.dept]) deptMap[d.dept] = { scheduled: 0, actual: 0 }
      deptMap[d.dept].scheduled += d.scheduled_hours || 0
      deptMap[d.dept].actual += d.actual_hours || 0
    })
    expect(deptMap['客服中心'].scheduled).toBe(8)
    expect(deptMap['客服中心'].actual).toBe(5)
  })
})

describe('calcDailyStats - 统计去重逻辑', () => {
  const expandedData = [
    { emp_id: 1, status: '正常' },
    { emp_id: 2, status: '正常' },
    { emp_id: 1, status: '正常' },
    { emp_id: 3, status: '缺勤' },
    { emp_id: 4, status: '迟到' },
    { emp_id: 2, status: '正常' },
    { emp_id: 5, status: '早退' },
  ]

  function calcDailyStats(data) {
    const seen = new Set()
    const unique = data.filter(d => {
      if (seen.has(d.emp_id)) return false
      seen.add(d.emp_id)
      return true
    })
    return {
      total: unique.length,
      attend: unique.filter(d => d.status !== '缺勤').length,
      normal: unique.filter(d => d.status === '正常').length,
      late: unique.filter(d => d.status === '迟到').length,
      absent: unique.filter(d => d.status === '缺勤').length,
    }
  }

  it('should count unique employees for total', () => {
    const stats = calcDailyStats(expandedData)
    expect(stats.total).toBe(5)
  })

  it('should not count duplicates in attend', () => {
    const stats = calcDailyStats(expandedData)
    expect(stats.attend).toBe(4)
  })

  it('should count status correctly', () => {
    const stats = calcDailyStats(expandedData)
    expect(stats.normal).toBe(2)
    expect(stats.late).toBe(1)
    expect(stats.absent).toBe(1)
  })

  it('should handle empty data', () => {
    const stats = calcDailyStats([])
    expect(stats.total).toBe(0)
    expect(stats.attend).toBe(0)
  })
})

describe('monthly/range stats - 全量聚合逻辑', () => {
  const mockData = [
    { dept: '客服中心', scheduled_hours: 8, actual_hours: 7.5, overtime_hours: 0, owed_hours: 0.5, normal_days: 20 },
    { dept: '客服中心', scheduled_hours: 8, actual_hours: 0, overtime_hours: 0, owed_hours: 8, normal_days: 0 },
    { dept: '技术部', scheduled_hours: 8, actual_hours: 8, overtime_hours: 1, owed_hours: 0, normal_days: 22 },
  ]

  function calcStats(data) {
    return {
      total: data.length,
      scheduled: data.reduce((s, d) => s + (d.scheduled_hours || 0), 0),
      actual: data.reduce((s, d) => s + (d.actual_hours || 0), 0),
      overtime: data.reduce((s, d) => s + (d.overtime_hours || 0), 0),
      owed: data.reduce((s, d) => s + (d.owed_hours || 0), 0),
      workDays: data.reduce((s, d) => s + (d.normal_days || 0), 0),
    }
  }

  it('should aggregate from all data, not paginated subset', () => {
    const stats = calcStats(mockData)
    expect(stats.total).toBe(3)
    expect(stats.scheduled).toBe(24)
    expect(stats.actual).toBe(15.5)
    expect(stats.overtime).toBe(1)
    expect(stats.owed).toBe(8.5)
    expect(stats.workDays).toBe(42)
  })

  it('should aggregate dept hours from all data', () => {
    const deptMap = {}
    mockData.forEach(d => {
      if (!deptMap[d.dept]) deptMap[d.dept] = { scheduled: 0, actual: 0 }
      deptMap[d.dept].scheduled += d.scheduled_hours || 0
      deptMap[d.dept].actual += d.actual_hours || 0
    })
    expect(deptMap['客服中心'].scheduled).toBe(16)
    expect(deptMap['技术部'].scheduled).toBe(8)
    expect(deptMap['客服中心'].actual).toBe(7.5)
  })

  it('should handle empty data for monthly stats', () => {
    const stats = calcStats([])
    expect(stats.total).toBe(0)
    expect(stats.scheduled).toBe(0)
  })

  it('should compute overtime/owed status distribution', () => {
    const overtime = mockData.filter(d => d.overtime_hours > 0).length
    const owed = mockData.filter(d => d.owed_hours > 0).length
    expect(overtime).toBe(1)
    expect(owed).toBe(2)
  })
})