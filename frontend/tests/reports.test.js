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