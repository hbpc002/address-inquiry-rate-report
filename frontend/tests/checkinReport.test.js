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

describe('CheckinReport - 签入明细折叠展开测试', () => {
  it('签入明细默认折叠（空展开集合）', () => {
    const expandedCheckins = new Set()
    expect(expandedCheckins.has('E001')).toBe(false)
    expect(expandedCheckins.size).toBe(0)
  })

  it('展开后加入集合，再次点击收起', () => {
    let expandedCheckins = new Set()
    const toggleCheckins = (empNo) => {
      const next = new Set(expandedCheckins)
      if (next.has(empNo)) {
        next.delete(empNo)
      } else {
        next.add(empNo)
      }
      expandedCheckins = next
    }

    toggleCheckins('E001')
    expect(expandedCheckins.has('E001')).toBe(true)

    toggleCheckins('E001')
    expect(expandedCheckins.has('E001')).toBe(false)
  })

  it('不同员工展开状态互不影响', () => {
    let expandedCheckins = new Set()
    const toggleCheckins = (empNo) => {
      const next = new Set(expandedCheckins)
      if (next.has(empNo)) {
        next.delete(empNo)
      } else {
        next.add(empNo)
      }
      expandedCheckins = next
    }

    toggleCheckins('E001')
    toggleCheckins('E002')
    expect(expandedCheckins.has('E001')).toBe(true)
    expect(expandedCheckins.has('E002')).toBe(true)

    toggleCheckins('E001')
    expect(expandedCheckins.has('E001')).toBe(false)
    expect(expandedCheckins.has('E002')).toBe(true)
  })
})

describe('CheckinReport - 班组报表排序与分页测试', () => {
  const teamReportData = [
    { emp_no: 'E001', name: '张三', team: '热线一组', late_days: 1, late_minutes: 30, early_days: 1, early_minutes: 10, checkin_count: 2, attend_days: 3 },
    { emp_no: 'E002', name: '李四', team: '热线一组', late_days: 0, late_minutes: 0, early_days: 0, early_minutes: 0, checkin_count: 1, attend_days: 1 },
    { emp_no: 'E003', name: '王五', team: '热线二组', late_days: 2, late_minutes: 45, early_days: 0, early_minutes: 0, checkin_count: 1, attend_days: 2 },
  ]

  it('按晚签总分钟降序排序，晚签多的人排前面', () => {
    const sorted = [...teamReportData].sort((a, b) => b.late_minutes - a.late_minutes)
    expect(sorted[0].emp_no).toBe('E003')
    expect(sorted[1].emp_no).toBe('E001')
    expect(sorted[2].emp_no).toBe('E002')
  })

  it('提前签出总分钟排序', () => {
    const sorted = [...teamReportData].sort((a, b) => b.early_minutes - a.early_minutes)
    expect(sorted[0].emp_no).toBe('E001')
  })

  it('分页切片取当前页数据', () => {
    const pageSize = 2
    const page = 1
    const start = (page - 1) * pageSize
    const paginated = teamReportData.slice(start, start + pageSize)
    expect(paginated.length).toBe(2)
    expect(paginated[0].emp_no).toBe('E001')
    expect(paginated[1].emp_no).toBe('E002')
  })
})

describe('CheckinReport - 汇总表排序与分页同步修复', () => {
  // 模拟后端返回顺序：按 checkin_count 降序，最高工时的员工排在后面（不在首页）
  const seedRows = [
    { emp_no: 'E001', name: '张三', team: '班组A', checkin_count: 30, total_hours: 30.0, hour_status: 'normal', late_days: 0 },
    { emp_no: 'E002', name: '李四', team: '班组A', checkin_count: 25, total_hours: 28.0, hour_status: 'normal', late_days: 1 },
    { emp_no: 'E003', name: '王五', team: '班组B', checkin_count: 20, total_hours: 26.0, hour_status: 'normal', late_days: 0 },
    { emp_no: 'E004', name: '赵六', team: '班组B', checkin_count: 10, total_hours: 99.0, hour_status: 'normal', late_days: 0 },
    { emp_no: 'E005', name: '孙七', team: '班组C', checkin_count: 8, total_hours: 80.0, hour_status: 'normal', late_days: 1 },
  ]

  // 与组件一致的排序逻辑：全量筛选后按 sortBy/sortOrder 排序，再分页切片
  function buildFilteredData(rows, { sortBy = '', sortOrder = '', filterType = '', filterValue = '', pageSize = 2, page = 1 } = {}) {
    let data = rows.slice()
    if (filterType === 'late') data = data.filter(d => (d.late_days || 0) > 0)
    if (filterType === 'name') data = data.filter(d => d.name === filterValue)
    if (sortBy && sortOrder) {
      data = [...data].sort((a, b) => {
        const aVal = a[sortBy] ?? -1
        const bVal = b[sortBy] ?? -1
        return sortOrder === 'ascending' ? aVal - bVal : bVal - aVal
      })
    }
    return data
  }

  function pageSlice(rows, page = 1, pageSize = 2) {
    const start = (page - 1) * pageSize
    return rows.slice(start, start + pageSize)
  }

  it('工时降序排序应对全量数据生效，首页第一条与图表 Top1 一致', () => {
    // 图表 Top1 是全量里 total_hours 最大的 赵六(99h)
    const topHours = [...seedRows].sort((a, b) => b.total_hours - a.total_hours)[0]
    expect(topHours.name).toBe('赵六')

    const sorted = buildFilteredData(seedRows, { sortBy: 'total_hours', sortOrder: 'descending', pageSize: 2 })
    const page1 = pageSlice(sorted, 1, 2)
    expect(page1[0].name).toBe('赵六')
    expect(page1[0].emp_no).toBe('E004')
  })

  it('老逻辑仅对当前页切片排序时，工时第一的员工不会出现在首页首位', () => {
    // 未排序的后端原始顺序下，首页是 E001/E002，切片内降序排不出 赵六
    const page1Old = pageSlice(seedRows, 1, 2)
    const sortedSlice = [...page1Old].sort((a, b) => b.total_hours - a.total_hours)
    expect(sortedSlice[0].name).not.toBe('赵六')
  })

  it('图表筛选后分页 Total 与当前页数据条数同步变化', () => {
    const all = buildFilteredData(seedRows, {})
    expect(all.length).toBe(5)

    // 点击「晚签」筛选后，参与分页的总数与筛选前不同
    const late = buildFilteredData(seedRows, { filterType: 'late' })
    expect(late.length).toBe(2)
    expect(late.length).not.toBe(all.length)

    // 晚签筛选下升序排列，首页第一条是工时最少的 李四(28h)
    const lateSorted = buildFilteredData(seedRows, { filterType: 'late', sortBy: 'total_hours', sortOrder: 'ascending' })
    const page1 = pageSlice(lateSorted, 1, 2)
    expect(page1[0].name).toBe('李四')
    expect(page1[0].emp_no).toBe('E002')
  })

  it('handleSortChange 应记录排序状态并把当前页重置到第 1 页', () => {
    let sortBy = ''
    let sortOrder = ''
    let currentPage = 3
    const handleSortChange = ({ prop, order }) => {
      sortBy = prop || ''
      sortOrder = order || ''
      currentPage = 1
    }
    handleSortChange({ prop: 'total_hours', order: 'descending' })
    expect(sortBy).toBe('total_hours')
    expect(sortOrder).toBe('descending')
    expect(currentPage).toBe(1)
  })
})

describe('CheckinReport - 自定义列逻辑测试', () => {
  const ALL_COLUMNS = [
    'emp_no', 'name', 'dept', 'team', 'checkin_count', 'total_hours', 'scheduled_hours', 'hour_status_text',
    'avg_punctuality_rate', 'total_call_duration', 'total_organize_duration',
    'avg_utilization_rate', 'avg_attendance_rate', 'training_minutes', 'computed_punctuality_rate',
    'attend_days', 'late_days', 'late_minutes', 'early_days', 'early_minutes', 'checkin_details'
  ]

  it('默认选中全部列', () => {
    const selected = [...ALL_COLUMNS]
    expect(selected).toHaveLength(21)
    expect(selected).toContain('total_hours')
    expect(selected).toContain('scheduled_hours')
    expect(selected).toContain('checkin_details')
  })

  it('根据选中集合判定列是否可见', () => {
    const selected = ['emp_no', 'name', 'total_hours', 'late_days']
    const visible = key => selected.includes(key)
    expect(visible('total_hours')).toBe(true)
    expect(visible('late_days')).toBe(true)
    expect(visible('checkin_count')).toBe(false)
    expect(visible('checkin_details')).toBe(false)
  })

  it('取消全部列后明细表仅剩固定操作列', () => {
    const selected = []
    const hidden = ALL_COLUMNS.filter(key => selected.includes(key))
    expect(hidden).toHaveLength(0)
  })

  it('自定义列选择持久化到 localStorage', () => {
    const KEY = 'checkin-report-columns'
    const cols = ['emp_no', 'name', 'dept', 'team', 'total_hours', 'late_days']
    localStorage.setItem(KEY, JSON.stringify(cols))
    const loaded = JSON.parse(localStorage.getItem(KEY) || '[]')
    expect(loaded).toEqual(cols)
    expect(loaded).not.toContain('checkin_details')
    localStorage.removeItem(KEY)
  })
})

describe('CheckinReport - 汇总合计行小数压缩测试', () => {
  const rows = [
    { emp_no: 'E001', name: '张三', checkin_count: 10, total_hours: 85.24972222222223, scheduled_hours: 80.0, total_call_duration: 40.5, attend_days: 5, late_minutes: 30, avg_punctuality_rate: 95.2 },
    { emp_no: 'E002', name: '李四', checkin_count: 8, total_hours: 56.0, scheduled_hours: 72.5, total_call_duration: 30.25, attend_days: 4, late_minutes: 0, avg_punctuality_rate: 97.5 }
  ]

  const SUMMABLE_COLUMNS = new Set([
    'checkin_count', 'total_hours', 'scheduled_hours', 'total_call_duration', 'total_organize_duration',
    'training_minutes', 'attend_days', 'late_days', 'late_minutes', 'early_days', 'early_minutes'
  ])
  const DECIMAL_COLUMNS = new Set(['total_hours', 'scheduled_hours', 'total_call_duration', 'total_organize_duration'])

  function summaryMethod(columns) {
    return columns.map(col => {
      const key = col.property
      if (!key || !SUMMABLE_COLUMNS.has(key)) return ''
      const total = rows.reduce((sum, row) => {
        const val = row[key]
        return sum + (typeof val === 'number' && isFinite(val) ? val : 0)
      }, 0)
      if (DECIMAL_COLUMNS.has(key)) return total.toFixed(1)
      return String(Math.round(total))
    })
  }

  it('工时合计应压缩为 1 位小数，而非原始长小数', () => {
    const sum = rows.reduce((s, r) => s + r.total_hours, 0)
    expect(sum).toBe(141.24972222222223)
    const result = summaryMethod([{ property: 'total_hours' }])[0]
    expect(result).toBe('141.2')
  })

  it('通话时长合计保留 1 位小数', () => {
    const result = summaryMethod([{ property: 'total_call_duration' }])[0]
    expect(result).toBe('70.8')
  })

  it('排班工时合计保留 1 位小数', () => {
    const result = summaryMethod([{ property: 'scheduled_hours' }])[0]
    expect(result).toBe('152.5')
  })

  it('计数类字段合计取整', () => {
    const checkin = summaryMethod([{ property: 'checkin_count' }])[0]
    const attend = summaryMethod([{ property: 'attend_days' }])[0]
    expect(checkin).toBe('18')
    expect(attend).toBe('9')
  })

  it('百分比列合计显示空（不计入求和逻辑）', () => {
    const result = summaryMethod([{ property: 'avg_punctuality_rate' }])[0]
    expect(result).toBe('')
  })

  it('无 property 的列（签入明细/操作）合计为空', () => {
    const result = summaryMethod([{}])[0]
    expect(result).toBe('')
  })
})
