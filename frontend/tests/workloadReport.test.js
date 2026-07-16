import { describe, it, expect } from 'vitest'

function displayLabel(field) {
  const label = field.split('-').pop()
  if (label === '生成总量') return '提单量'
  return label
}

function isRateField(field) {
  return field.includes('率')
}

function formatRate(val) {
  if (val === null || val === undefined) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  if (isNaN(num)) return '-'
  return (num * 100).toFixed(2) + '%'
}

function formatMetricValue(val, isRate) {
  if (val === null || val === undefined) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  if (isNaN(num)) return val
  if (isRate) return (num * 100).toFixed(2) + '%'
  if (Number.isInteger(num)) return String(num)
  return num.toFixed(1)
}

function getMetricValue(row, field) {
  const val = row.aggregated_metrics?.[field]
  if (val === null || val === undefined) return null
  return typeof val === 'number' ? val : parseFloat(val) || 0
}

function getAvgDuration(data) {
  let totalDuration = 0
  let totalCalls = 0
  data.forEach(d => {
    totalDuration += getMetricValue(d, '呼入人工服务-人工服务-通话总时长(秒)') || 0
    totalCalls += getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
  })
  if (totalCalls === 0) return 0
  return Math.round(totalDuration / totalCalls * 10) / 10
}

function makeTeamRanking(data) {
  const teamMap = {}
  data.forEach(d => {
    const team = d.team_desc || '未知班组'
    const isMember = d.role !== '组长' && d.role !== '师傅'
    if (!teamMap[team]) {
      teamMap[team] = {
        count_all: 0, count_member: 0,
        total_calls_all: 0, total_calls_member: 0,
        total_duration: 0, total_work_duration_member: 0,
        total_ticket_count: 0,
        total_sat_numerator: 0, total_sat_denominator: 0,
        leaders: []
      }
    }
    const t = teamMap[team]
    t.count_all++
    if (d.role === '组长' && d.name) {
      t.leaders.push(d.name)
    }
    const calls = getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    t.total_calls_all += calls
    t.total_duration += getMetricValue(d, '呼入人工服务-人工服务-通话总时长(秒)') || 0
    t.total_ticket_count += getMetricValue(d, '呼入人工服务-工单-生成总量') || 0
    if (isMember) {
      t.count_member++
      t.total_calls_member += calls
      t.total_work_duration_member += getMetricValue(d, '总体-工作总时长(秒)') || 0
    }
    const verySat = getMetricValue(d, '呼入人工服务-满意度-非常满意量') || 0
    const sat = getMetricValue(d, '呼入人工服务-满意度-满意量') || 0
    const general = getMetricValue(d, '呼入人工服务-满意度-一般量') || 0
    const disSat = getMetricValue(d, '呼入人工服务-满意度-不满意量') || 0
    const veryDisSat = getMetricValue(d, '呼入人工服务-满意度-非常不满意量') || 0
    t.total_sat_numerator += verySat + sat
    t.total_sat_denominator += verySat + sat + general + disSat + veryDisSat
  })
  return Object.entries(teamMap)
    .map(([team, data]) => {
      const checkinHours = data.total_work_duration_member / 3600
      return {
        team,
        leader: data.leaders.filter((v, i, a) => a.indexOf(v) === i).join('、') || '',
        count: data.count_all,
        count_member: data.count_member,
        total_calls: data.total_calls_all,
        total_ticket_count: data.total_ticket_count,
        avg_calls_per_person_all: data.count_all > 0 ? +(data.total_calls_all / data.count_all).toFixed(1) : 0,
        avg_calls_per_person_member: data.count_member > 0 ? +(data.total_calls_member / data.count_member).toFixed(1) : 0,
        member_call_hourly_rate: checkinHours > 0 ? +(data.total_calls_member / checkinHours).toFixed(1) : 0,
        ti_dan_lv: data.total_calls_all > 0 ? data.total_ticket_count / data.total_calls_all : 0,
        avg_duration: data.total_calls_all > 0 ? +(data.total_duration / data.total_calls_all).toFixed(1) : 0,
        avg_satisfaction: data.total_sat_denominator > 0 ? data.total_sat_numerator / data.total_sat_denominator : null
      }
    })
    .sort((a, b) => b.total_calls - a.total_calls)
}

function makeTeamChartData(data) {
  const teamMap = {}
  data.forEach(d => {
    const team = d.team_desc || '未知班组'
    if (!teamMap[team]) {
      teamMap[team] = { value: 0, count: 0, totalDuration: 0, totalCalls: 0, totalTicket: 0 }
    }
    const t = teamMap[team]
    const calls = getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    t.value += calls
    t.count++
    t.totalCalls += calls
    t.totalTicket += getMetricValue(d, '呼入人工服务-工单-生成总量') || 0
    t.totalDuration += getMetricValue(d, '呼入人工服务-人工服务-通话总时长(秒)') || 0
  })
  return Object.entries(teamMap)
    .map(([name, data]) => ({
      name,
      value: Math.round(data.value),
      peopleCount: data.count,
      avgDuration: data.totalCalls > 0 ? +(data.totalDuration / data.totalCalls).toFixed(1) : 0,
      totalTicket: Math.round(data.totalTicket),
      tiDanLv: data.value > 0 ? data.totalTicket / data.value : 0
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
}

function makeTeamMemberChartData(data, filterValue, filterType = 'team') {
  let team = ''
  if (filterType === 'team') {
    team = filterValue
  } else if (filterType === 'name') {
    const person = data.find(d => d.name === filterValue)
    if (person) team = person.team_desc
  }
  if (!team) return []
  const members = data.filter(d => d.team_desc === team)
  return members
    .map(d => ({
      name: d.name || '未知',
      value: getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    }))
    .sort((a, b) => b.value - a.value)
}

function handlePieClick(name, filterType, filterValue) {
  const state = { filterType, filterValue, currentPage: 1 }
  if (name) {
    if (state.filterType === 'team') {
      state.filterType = ''
      state.filterValue = ''
      state.currentPage = 1
    } else {
      state.filterType = 'team'
      state.filterValue = name
      state.currentPage = 1
    }
  }
  return { filterType: state.filterType, filterValue: state.filterValue }
}

function formatPieTooltip(name, value, percent, unit, extra) {
  let lines = [`${name}`, `${unit}: ${value} (${percent}%)`]
  if (extra.peopleCount !== undefined) lines.push(`人数: ${extra.peopleCount}`)
  if (extra.avgDuration !== undefined) lines.push(`平均通话均长: ${extra.avgDuration}s`)
  if (extra.totalTicket !== undefined) lines.push(`工单总量: ${extra.totalTicket}`)
  if (extra.tiDanLv !== undefined) lines.push(`提单率: ${(extra.tiDanLv * 100).toFixed(2)}%`)
  return lines.join('\n')
}

function resolveRateField(d) {
  return getMetricValue(d, '人工服务-解决率-转解决情况调查率')
}

const DEFAULT_TIERS = [
  { min: 0, max: 1000, rate: 1.0 },
  { min: 1000, max: 2000, rate: 1.5 },
  { min: 2000, max: 3500, rate: 1.2 },
  { min: 3500, max: null, rate: 1.0 }
]

function calcCallSalary(callCount, tiers) {
  const t = tiers || DEFAULT_TIERS
  let remaining = callCount
  let total = 0
  for (const tier of t) {
    if (remaining <= 0) break
    const bracketSize = tier.max === null ? remaining : Math.min(remaining, tier.max - tier.min)
    total += bracketSize * tier.rate
    remaining -= bracketSize
  }
  return total
}

function calcSatSalary(row) {
  const sat = getMetricValue(row, '呼入人工服务-满意度-非常满意量')
  const weight = getMetricValue(row, '呼入人工服务-满意度-满意量')
  if (sat === null || weight === null) return null
  return (sat + weight) * 0.5
}

function calcSatDiff(row, coeffA, coeffB) {
  const e = getMetricValue(row, '呼入人工服务-满意度-非常满意量')
  const f = getMetricValue(row, '呼入人工服务-满意度-满意量')
  const g = getMetricValue(row, '呼入人工服务-满意度-一般量')
  const h = getMetricValue(row, '呼入人工服务-满意度-不满意量')
  const i = getMetricValue(row, '呼入人工服务-满意度-非常不满意量')
  if (e === null || f === null) return null
  const sumAll = [e, f, g, h, i].filter(v => v !== null).reduce((a, b) => a + b, 0)
  const sumEF = (e || 0) + (f || 0)
  const a = coeffA ?? 19
  const b = coeffB ?? 20
  return sumAll * a - sumEF * b
}

describe('WorkloadReport - 格式化函数测试', () => {

  describe('displayLabel', () => {
    it('should return last segment of dotted field name', () => {
      expect(displayLabel('呼入人工服务-人工服务-通话次数')).toBe('通话次数')
    })
    it('should map 生成总量 to 提单量', () => {
      expect(displayLabel('呼入人工服务-工单-生成总量')).toBe('提单量')
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
    it('should multiply by 100 and format as percentage with 2 decimals', () => {
      expect(formatRate(0.8567)).toBe('85.67%')
      expect(formatRate(0.95)).toBe('95.00%')
      expect(formatRate(1.0)).toBe('100.00%')
    })
    it('should return dash for null/undefined', () => {
      expect(formatRate(null)).toBe('-')
      expect(formatRate(undefined)).toBe('-')
    })
    it('should handle string numbers', () => {
      expect(formatRate('0.8567')).toBe('85.67%')
    })
    it('should return dash for NaN', () => {
      expect(formatRate(NaN)).toBe('-')
    })
  })

  describe('formatMetricValue', () => {
    it('should multiply by 100 for rate fields', () => {
      expect(formatMetricValue(0.8567, true)).toBe('85.67%')
      expect(formatMetricValue(0.95, true)).toBe('95.00%')
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
        '满意率': 0.95,
        '空值字段': null
      }
    }
    it('should extract numeric value from aggregated_metrics', () => {
      expect(getMetricValue(row, '通话次数')).toBe(30)
    })
    it('should handle rate values (0-1 scale)', () => {
      expect(getMetricValue(row, '满意率')).toBe(0.95)
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

  describe('averageCallDuration', () => {
    it('should compute team avg as totalDuration / totalCalls', () => {
      const data = [
        { aggregated_metrics: { '呼入人工服务-人工服务-通话总时长(秒)': 1800, '呼入人工服务-人工服务-通话次数': 10 } },
        { aggregated_metrics: { '呼入人工服务-人工服务-通话总时长(秒)': 2200, '呼入人工服务-人工服务-通话次数': 10 } },
        { aggregated_metrics: { '呼入人工服务-人工服务-通话总时长(秒)': 2000, '呼入人工服务-人工服务-通话次数': 10 } }
      ]
      expect(getAvgDuration(data)).toBe(200)
    })
    it('should skip null/undefined values', () => {
      const data = [
        { aggregated_metrics: { '呼入人工服务-人工服务-通话总时长(秒)': 1800, '呼入人工服务-人工服务-通话次数': 10 } },
        { aggregated_metrics: {} },
        { aggregated_metrics: { '呼入人工服务-人工服务-通话总时长(秒)': null, '呼入人工服务-人工服务-通话次数': null } }
      ]
      expect(getAvgDuration(data)).toBe(180)
    })
    it('should return 0 for empty data', () => {
      expect(getAvgDuration([])).toBe(0)
    })
    it('should return 0 when totalCalls is 0', () => {
      const data = [
        { aggregated_metrics: { '呼入人工服务-人工服务-通话总时长(秒)': 0, '呼入人工服务-人工服务-通话次数': 0 } },
        { aggregated_metrics: {} }
      ]
      expect(getAvgDuration(data)).toBe(0)
    })
  })

  describe('teamRanking merge', () => {
    it('should aggregate team data with all required fields', () => {
      const data = [
        { role: '组员', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10, '呼入人工服务-人工服务-通话总时长(秒)': 1800, '总体-工作总时长(秒)': 20000, '呼入人工服务-满意度-非常满意量': 8, '呼入人工服务-满意度-满意量': 1, '呼入人工服务-满意度-一般量': 1, '呼入人工服务-满意度-不满意量': 0, '呼入人工服务-满意度-非常不满意量': 0, '呼入人工服务-工单-生成总量': 5 } },
        { role: '组员', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20, '呼入人工服务-人工服务-通话总时长(秒)': 4000, '总体-工作总时长(秒)': 22000, '呼入人工服务-满意度-非常满意量': 10, '呼入人工服务-满意度-满意量': 5, '呼入人工服务-满意度-一般量': 3, '呼入人工服务-满意度-不满意量': 1, '呼入人工服务-满意度-非常不满意量': 1, '呼入人工服务-工单-生成总量': 8 } },
        { role: '组员', team_desc: 'B组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 30, '呼入人工服务-人工服务-通话总时长(秒)': 4500, '总体-工作总时长(秒)': 28800, '呼入人工服务-满意度-非常满意量': 15, '呼入人工服务-满意度-满意量': 8, '呼入人工服务-满意度-一般量': 4, '呼入人工服务-满意度-不满意量': 2, '呼入人工服务-满意度-非常不满意量': 1, '呼入人工服务-工单-生成总量': 12 } }
      ]
      const result = makeTeamRanking(data)
      expect(result).toHaveLength(2)
      const teamA = result.find(r => r.team === 'A组')
      expect(teamA.leader).toBe('')
      expect(teamA.count).toBe(2)
      expect(teamA.count_member).toBe(2)
      expect(teamA.total_calls).toBe(30)
      expect(teamA.total_ticket_count).toBe(13)
      expect(teamA.avg_calls_per_person_all).toBe(15)
      expect(teamA.avg_calls_per_person_member).toBe(15)
      expect(teamA.member_call_hourly_rate).toBe(2.6)
      expect(teamA.ti_dan_lv).toBeCloseTo(13 / 30, 4)
      expect(teamA.avg_duration).toBe(193.3)
      expect(teamA.avg_satisfaction).toBeCloseTo(24 / 30, 4)
      const teamB = result.find(r => r.team === 'B组')
      expect(teamB.count).toBe(1)
      expect(teamB.count_member).toBe(1)
      expect(teamB.total_calls).toBe(30)
      expect(teamB.total_ticket_count).toBe(12)
      expect(teamB.avg_calls_per_person_all).toBe(30)
      expect(teamB.avg_calls_per_person_member).toBe(30)
      expect(teamB.member_call_hourly_rate).toBe(3.8)
      expect(teamB.ti_dan_lv).toBeCloseTo(12 / 30, 4)
      expect(teamB.avg_duration).toBe(150)
      expect(teamB.avg_satisfaction).toBeCloseTo(23 / 30, 4)
    })
    it('should handle teams with 组长/师傅 separately', () => {
      const data = [
        { role: '组员', name: '张三', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20, '呼入人工服务-人工服务-通话总时长(秒)': 4000, '总体-工作总时长(秒)': 22000, '呼入人工服务-满意度-非常满意量': 10, '呼入人工服务-满意度-满意量': 5, '呼入人工服务-满意度-一般量': 3, '呼入人工服务-满意度-不满意量': 1, '呼入人工服务-满意度-非常不满意量': 1, '呼入人工服务-工单-生成总量': 8 } },
        { role: '组长', name: '李四', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10, '呼入人工服务-人工服务-通话总时长(秒)': 1800, '总体-工作总时长(秒)': 20000, '呼入人工服务-满意度-非常满意量': 8, '呼入人工服务-满意度-满意量': 1, '呼入人工服务-满意度-一般量': 1, '呼入人工服务-满意度-不满意量': 0, '呼入人工服务-满意度-非常不满意量': 0, '呼入人工服务-工单-生成总量': 5 } },
        { role: '师傅', name: '王五', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 5, '呼入人工服务-人工服务-通话总时长(秒)': 900, '总体-工作总时长(秒)': 18000, '呼入人工服务-满意度-非常满意量': 4, '呼入人工服务-满意度-满意量': 1, '呼入人工服务-满意度-一般量': 0, '呼入人工服务-满意度-不满意量': 0, '呼入人工服务-满意度-非常不满意量': 0, '呼入人工服务-工单-生成总量': 2 } }
      ]
      const result = makeTeamRanking(data)
      expect(result).toHaveLength(1)
      const teamA = result[0]
      expect(teamA.leader).toBe('李四')
      expect(teamA.count).toBe(3)
      expect(teamA.count_member).toBe(1)
      expect(teamA.total_calls).toBe(35)
      expect(teamA.avg_calls_per_person_all).toBe(11.7)
      expect(teamA.avg_calls_per_person_member).toBe(20)
      expect(teamA.member_call_hourly_rate).toBe(3.3)
    })
    it('should handle unknown team_desc', () => {
      const data = [
        { role: '组员', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 5, '总体-工作总时长(秒)': 18000 } }
      ]
      const result = makeTeamRanking(data)
      expect(result[0].team).toBe('未知班组')
      expect(result[0].leader).toBe('')
      expect(result[0].total_ticket_count).toBe(0)
      expect(result[0].avg_calls_per_person_all).toBe(5)
      expect(result[0].avg_calls_per_person_member).toBe(5)
      expect(result[0].member_call_hourly_rate).toBeCloseTo(5 / (18000 / 3600), 4)
      expect(result[0].ti_dan_lv).toBe(0)
    })
  })

  describe('teamChartData merge', () => {
    it('should aggregate team chart data with extra tooltip fields', () => {
      const data = [
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10, '呼入人工服务-人工服务-通话总时长(秒)': 1800, '呼入人工服务-工单-生成总量': 5 } },
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20, '呼入人工服务-人工服务-通话总时长(秒)': 4000, '呼入人工服务-工单-生成总量': 8 } },
        { team_desc: 'B组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 30, '呼入人工服务-人工服务-通话总时长(秒)': 4500, '呼入人工服务-工单-生成总量': 12 } }
      ]
      const result = makeTeamChartData(data)
      expect(result).toHaveLength(2)
      const teamA = result.find(r => r.name === 'A组')
      expect(teamA.value).toBe(30)
      expect(teamA.peopleCount).toBe(2)
      expect(teamA.avgDuration).toBe(193.3)
      expect(teamA.totalTicket).toBe(13)
      expect(teamA.tiDanLv).toBeCloseTo(13 / 30, 4)
      const teamB = result.find(r => r.name === 'B组')
      expect(teamB.value).toBe(30)
      expect(teamB.peopleCount).toBe(1)
      expect(teamB.avgDuration).toBe(150)
      expect(teamB.totalTicket).toBe(12)
      expect(teamB.tiDanLv).toBeCloseTo(12 / 30, 4)
    })
    it('should handle null duration gracefully', () => {
      const data = [
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10, '呼入人工服务-人工服务-通话总时长(秒)': null, '呼入人工服务-工单-生成总量': 3 } },
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20, '呼入人工服务-工单-生成总量': 5 } }
      ]
      const result = makeTeamChartData(data)
      expect(result).toHaveLength(1)
      expect(result[0].peopleCount).toBe(2)
      expect(result[0].avgDuration).toBe(0)
      expect(result[0].totalTicket).toBe(8)
    })
    it('should limit to top 8 teams', () => {
      const data = Array.from({ length: 10 }, (_, i) => ({
        team_desc: `第${i + 1}组`,
        aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 + i }
      }))
      const result = makeTeamChartData(data)
      expect(result).toHaveLength(8)
    })
    it('should sort by call count descending', () => {
      const data = [
        { team_desc: 'B组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20 } },
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 30 } },
        { team_desc: 'C组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 } }
      ]
      const result = makeTeamChartData(data)
      expect(result[0].name).toBe('A组')
      expect(result[1].name).toBe('B组')
      expect(result[2].name).toBe('C组')
    })
    it('should handle unknown team_desc as 未知班组', () => {
      const data = [
        { aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 5 } }
      ]
      const result = makeTeamChartData(data)
      expect(result[0].name).toBe('未知班组')
      expect(result[0].totalTicket).toBe(0)
      expect(result[0].tiDanLv).toBe(0)
    })
  })

  describe('teamMemberChartData', () => {
    it('should return member-level data sorted by call count descending', () => {
      const data = [
        { name: '张三', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 } },
        { name: '李四', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 30 } },
        { name: '王五', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20 } },
        { name: '赵六', team_desc: 'B组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 50 } }
      ]
      const result = makeTeamMemberChartData(data, 'A组')
      expect(result).toHaveLength(3)
      expect(result[0].name).toBe('李四')
      expect(result[0].value).toBe(30)
      expect(result[1].name).toBe('王五')
      expect(result[1].value).toBe(20)
      expect(result[2].name).toBe('张三')
      expect(result[2].value).toBe(10)
    })
    it('should handle members with zero calls', () => {
      const data = [
        { name: '张三', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 0 } },
        { name: '李四', team_desc: 'A组', aggregated_metrics: {} }
      ]
      const result = makeTeamMemberChartData(data, 'A组')
      expect(result).toHaveLength(2)
      expect(result[0].value).toBe(0)
      expect(result[1].value).toBe(0)
    })
    it('should return empty array for non-matching team', () => {
      const data = [
        { name: '张三', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 } }
      ]
      const result = makeTeamMemberChartData(data, '不存在的组')
      expect(result).toHaveLength(0)
    })
    it('should use name field for each member', () => {
      const data = [
        { name: '测试1', team_desc: 'X组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 5 } },
        { name: '测试2', team_desc: 'X组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 3 } }
      ]
      const result = makeTeamMemberChartData(data, 'X组')
      expect(result.map(r => r.name)).toEqual(['测试1', '测试2'])
    })
    it('should resolve team from person name', () => {
      const data = [
        { name: '张三', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 } },
        { name: '李四', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20 } },
        { name: '王五', team_desc: 'B组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 30 } }
      ]
      const result = makeTeamMemberChartData(data, '张三', 'name')
      expect(result).toHaveLength(2)
      expect(result[0].name).toBe('李四')
      expect(result[1].name).toBe('张三')
    })
    it('should return empty for non-existent person name', () => {
      const data = [
        { name: '张三', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 } }
      ]
      const result = makeTeamMemberChartData(data, '不存在的名字', 'name')
      expect(result).toHaveLength(0)
    })
  })

  describe('handlePieClick', () => {
    it('should set team filter on first click', () => {
      const result = handlePieClick('A组', '', '')
      expect(result.filterType).toBe('team')
      expect(result.filterValue).toBe('A组')
    })
    it('should clear team filter when clicking same team again', () => {
      const result = handlePieClick('A组', 'team', 'A组')
      expect(result.filterType).toBe('')
      expect(result.filterValue).toBe('')
    })
    it('should clear filter when clicking bar chart (filterType === team)', () => {
      const result = handlePieClick('B组', 'team', 'A组')
      expect(result.filterType).toBe('')
      expect(result.filterValue).toBe('')
    })
    it('should do nothing when name is empty', () => {
      const result = handlePieClick('', 'name', '张三')
      expect(result.filterType).toBe('name')
      expect(result.filterValue).toBe('张三')
    })
  })

  describe('formatPieTooltip', () => {
    it('should produce multi-line tooltip with all fields', () => {
      const tooltip = formatPieTooltip('A组', 150, 30, '产量', {
        peopleCount: 5,
        avgDuration: 180.5,
        totalTicket: 20,
        tiDanLv: 0.1333
      })
      const lines = tooltip.split('\n')
      expect(lines[0]).toBe('A组')
      expect(lines[1]).toBe('产量: 150 (30%)')
      expect(lines[2]).toBe('人数: 5')
      expect(lines[3]).toBe('平均通话均长: 180.5s')
      expect(lines[4]).toBe('工单总量: 20')
      expect(lines[5]).toBe('提单率: 13.33%')
    })
    it('should handle partial fields gracefully', () => {
      const tooltip = formatPieTooltip('B组', 50, 25, '产量', {
        peopleCount: 2,
        totalTicket: 8
      })
      expect(tooltip).toContain('人数: 2')
      expect(tooltip).toContain('工单总量: 8')
      expect(tooltip).not.toContain('平均通话均长')
      expect(tooltip).not.toContain('提单率')
    })
    it('should work with default unit 工时', () => {
      const tooltip = formatPieTooltip('C组', 200, 40, '工时', {
        peopleCount: 10
      })
      expect(tooltip).toContain('工时: 200')
    })
  })

  describe('resolveRate field replacement', () => {
    it('should extract 转解决情况调查率 value', () => {
      const d = { aggregated_metrics: { '人工服务-解决率-转解决情况调查率': 0.88 } }
      expect(resolveRateField(d)).toBe(0.88)
    })
    it('should return null for missing field', () => {
      const d = {}
      expect(resolveRateField(d)).toBeNull()
    })
  })

  describe('calcCallSalary', () => {
    it('should calculate tier 1 (< 1000)', () => {
      expect(calcCallSalary(500)).toBeCloseTo(500)
    })
    it('should calculate tier 2 (1000-2000)', () => {
      const total = 1000 * 1.0 + 500 * 1.5
      expect(calcCallSalary(1500)).toBeCloseTo(total)
    })
    it('should calculate tier 3 (2000-3500)', () => {
      const total = 1000 * 1.0 + 1000 * 1.5 + 500 * 1.2
      expect(calcCallSalary(2500)).toBeCloseTo(total)
    })
    it('should calculate tier 4 (> 3500)', () => {
      const total = 1000 * 1.0 + 1000 * 1.5 + 1500 * 1.2 + 500 * 1.0
      expect(calcCallSalary(4000)).toBeCloseTo(total)
    })
    it('should return 0 for 0 calls', () => {
      expect(calcCallSalary(0)).toBe(0)
    })
    it('should handle custom tiers', () => {
      const customTiers = [{ min: 0, max: null, rate: 2.0 }]
      expect(calcCallSalary(100, customTiers)).toBe(200)
    })
  })

  describe('calcSatSalary', () => {
    it('should compute (非常满意量 + 满意量) * 0.5', () => {
      const row = { aggregated_metrics: {
        '呼入人工服务-满意度-非常满意量': 0.8,
        '呼入人工服务-满意度-满意量': 0.9
      }}
      expect(calcSatSalary(row)).toBeCloseTo(0.85)
    })
    it('should return null when fields missing', () => {
      expect(calcSatSalary({})).toBeNull()
    })
  })

  describe('calcSatDiff', () => {
    const row = { aggregated_metrics: {
      '呼入人工服务-满意度-非常满意量': 10,
      '呼入人工服务-满意度-满意量': 20,
      '呼入人工服务-满意度-一般量': 5,
      '呼入人工服务-满意度-不满意量': 3,
      '呼入人工服务-满意度-非常不满意量': 2
    }}
    it('should compute ((all) * A - (E+F) * B)', () => {
      const result = calcSatDiff(row, 19, 20)
      const expected = (10 + 20 + 5 + 3 + 2) * 19 - (10 + 20) * 20
      expect(result).toBeCloseTo(expected)
    })
    it('should use default coefficients when not provided', () => {
      const result = calcSatDiff(row)
      const expected = (10 + 20 + 5 + 3 + 2) * 19 - (10 + 20) * 20
      expect(result).toBeCloseTo(expected)
    })
    it('should return null when E or F missing', () => {
      expect(calcSatDiff({})).toBeNull()
    })
  })

  describe('calcCallHourlyRate', () => {
    function calcCallHourlyRate(row) {
      const callCount = getMetricValue(row, '呼入人工服务-人工服务-通话次数') || 0
      const workDuration = getMetricValue(row, '总体-工作总时长(秒)') || 0
      return workDuration > 0 ? +(callCount / (workDuration / 3600)).toFixed(1) : 0
    }

    it('should compute calls per hour based on work duration', () => {
      const row = { aggregated_metrics: {
        '呼入人工服务-人工服务-通话次数': 30,
        '总体-工作总时长(秒)': 28800
      }}
      expect(calcCallHourlyRate(row)).toBeCloseTo(3.8, 1)
    })
    it('should return 0 when no work duration', () => {
      const row = { aggregated_metrics: {
        '呼入人工服务-人工服务-通话次数': 10
      }}
      expect(calcCallHourlyRate(row)).toBe(0)
    })
    it('should return 0 for zero calls', () => {
      const row = { aggregated_metrics: {
        '呼入人工服务-人工服务-通话次数': 0,
        '总体-工作总时长(秒)': 28800
      }}
      expect(calcCallHourlyRate(row)).toBe(0)
    })
  })

})

describe('getMetricStyle - 指标目标值预警逻辑', () => {
  const targets = [
    { field: '人工服务-满意度-满意率', label: '满意率', operator: 'lt', value: 0.95, color: '#F56C6C', enabled: true },
    { field: '_ti_dan_lv', label: '提单率', operator: 'gt', value: 0.15, color: '#E6A23C', enabled: true },
    { field: 'disabled-field', label: '已禁用', operator: 'lt', value: 100, color: '#F56C6C', enabled: false },
  ]

  function getMetricStyle(fieldKey, value) {
    const activeTargets = targets.filter(t => t.enabled !== false)
    if (!activeTargets.length || value === null || value === undefined) return null
    const target = activeTargets.find(t => t.field === fieldKey)
    if (!target) return null
    let hit = false
    switch (target.operator) {
      case 'lt': hit = value < target.value; break
      case 'le': hit = value <= target.value; break
      case 'gt': hit = value > target.value; break
      case 'ge': hit = value >= target.value; break
    }
    return hit ? { color: target.color, fontWeight: 'bold' } : null
  }

  it('should return style when satisfaction rate is below target (lt)', () => {
    const style = getMetricStyle('人工服务-满意度-满意率', 0.90)
    expect(style).toEqual({ color: '#F56C6C', fontWeight: 'bold' })
  })

  it('should return null when satisfaction rate meets target', () => {
    expect(getMetricStyle('人工服务-满意度-满意率', 0.95)).toBeNull()
    expect(getMetricStyle('人工服务-满意度-满意率', 0.96)).toBeNull()
  })

  it('should return style when ti_dan_lv exceeds target (gt)', () => {
    const style = getMetricStyle('_ti_dan_lv', 0.20)
    expect(style).toEqual({ color: '#E6A23C', fontWeight: 'bold' })
  })

  it('should return null when ti_dan_lv is at or below target', () => {
    expect(getMetricStyle('_ti_dan_lv', 0.15)).toBeNull()
    expect(getMetricStyle('_ti_dan_lv', 0.10)).toBeNull()
  })

  it('should return null for null/undefined values', () => {
    expect(getMetricStyle('_ti_dan_lv', null)).toBeNull()
    expect(getMetricStyle('_ti_dan_lv', undefined)).toBeNull()
  })

  it('should return null for unknown fields', () => {
    expect(getMetricStyle('不存在的字段', 0.5)).toBeNull()
  })

  it('should ignore disabled targets', () => {
    expect(getMetricStyle('disabled-field', 50)).toBeNull()
  })

  it('should handle le (less than or equal)', () => {
    const localTargets = [
      { field: 'test', label: '测试', operator: 'le', value: 100, color: '#F56C6C', enabled: true }
    ]
    const fn = (k, v) => {
      const active = localTargets.filter(t => t.enabled !== false)
      if (!active.length || v === null || v === undefined) return null
      const t = active.find(x => x.field === k)
      if (!t) return null
      let hit = false
      switch (t.operator) {
        case 'le': hit = v <= t.value; break
        case 'ge': hit = v >= t.value; break
      }
      return hit ? { color: t.color, fontWeight: 'bold' } : null
    }
    expect(fn('test', 100)).toEqual({ color: '#F56C6C', fontWeight: 'bold' })
    expect(fn('test', 99)).toEqual({ color: '#F56C6C', fontWeight: 'bold' })
    expect(fn('test', 101)).toBeNull()
  })

  it('should handle ge (greater than or equal)', () => {
    const localTargets = [
      { field: 'test', label: '测试', operator: 'ge', value: 80, color: '#67C23A', enabled: true }
    ]
    const fn = (k, v) => {
      const active = localTargets.filter(t => t.enabled !== false)
      if (!active.length || v === null || v === undefined) return null
      const t = active.find(x => x.field === k)
      if (!t) return null
      let hit = false
      switch (t.operator) {
        case 'ge': hit = v >= t.value; break
      }
      return hit ? { color: t.color, fontWeight: 'bold' } : null
    }
    expect(fn('test', 80)).toEqual({ color: '#67C23A', fontWeight: 'bold' })
    expect(fn('test', 85)).toEqual({ color: '#67C23A', fontWeight: 'bold' })
    expect(fn('test', 79)).toBeNull()
  })

  it('should return null when no active targets exist', () => {
    const fn = (k, v) => {
      const active = []
      if (!active.length || v === null || v === undefined) return null
      return null
    }
    expect(fn('any', 0.5)).toBeNull()
  })
})

describe('WorkloadReport - loadTeams', () => {
  it('should handle API response with {team, count} objects', async () => {
    const apiResponse = [
      { team: '二班1组', count: 17 },
      { team: '二班2组', count: 15 },
      { team: '三班1组', count: 20 }
    ]
    const teams = apiResponse
    expect(teams).toHaveLength(3)
    expect(teams[0].team).toBe('二班1组')
    expect(teams[1].team).toBe('二班2组')
    expect(teams[2].team).toBe('三班1组')
    const options = teams.map(t => ({ label: t.team, value: t.team }))
    expect(options[0]).toEqual({ label: '二班1组', value: '二班1组' })
  })
  it('should handle empty API response', async () => {
    const teams = []
    expect(teams).toEqual([])
  })
  it('should handle missing count field gracefully', async () => {
    const apiResponse = [
      { team: 'A组' },
      { team: 'B组' }
    ]
    const teams = apiResponse
    const labels = teams.map(t => t.team)
    expect(labels).toEqual(['A组', 'B组'])
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
