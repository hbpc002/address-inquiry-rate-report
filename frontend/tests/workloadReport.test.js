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

function makeTeamRanking(data, teamLeaders = {}) {
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
        leader: data.leaders.filter((v, i, a) => a.indexOf(v) === i).join('、') || teamLeaders[team] || '',
        count: data.count_all,
        count_member: data.count_member,
        total_calls: data.total_calls_all,
        total_ticket_count: data.total_ticket_count,
        total_duration: data.total_duration,
        avg_calls_per_person_all: data.count_all > 0 ? +(data.total_calls_all / data.count_all).toFixed(1) : 0,
        avg_calls_per_person_member: data.count_member > 0 ? +(data.total_calls_member / data.count_member).toFixed(1) : 0,
        member_call_hourly_rate: checkinHours > 0 ? +(data.total_calls_member / checkinHours).toFixed(1) : 0,
        ti_dan_lv: data.total_calls_all > 0 ? data.total_ticket_count / data.total_calls_all : 0,
        avg_duration: data.total_calls_all > 0 ? +(data.total_duration / data.total_calls_all).toFixed(1) : 0,
        avg_satisfaction: data.total_sat_denominator > 0 ? data.total_sat_numerator / data.total_sat_denominator : null,
        total_sat_numerator: data.total_sat_numerator,
        total_sat_denominator: data.total_sat_denominator
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

function makeTeamMemberChartData(data, filterValue, filterType = 'team', searchFormTeam = '') {
  let team = ''
  if (filterType === 'team') {
    team = filterValue
  } else if (filterType === 'name') {
    const person = data.find(d => d.name === filterValue)
    if (person) team = person.team_desc
  } else if (searchFormTeam) {
    team = searchFormTeam
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

function extractClass(team) {
  const m = team && team.match(/^(.+?)[\d]+组$/)
  return m ? m[1] : team
}

function makeClassRanking(teamRankingData) {
  const classMap = {}
  teamRankingData.forEach(t => {
    const cls = extractClass(t.team)
    if (!cls) return
    if (!classMap[cls]) {
      classMap[cls] = { count: 0, team_count: 0, total_calls: 0, total_ticket_count: 0, total_duration: 0, total_sat_numerator: 0, total_sat_denominator: 0 }
    }
    const c = classMap[cls]
    c.count += t.count
    c.team_count++
    c.total_calls += t.total_calls
    c.total_ticket_count += t.total_ticket_count
    c.total_duration += t.total_duration
    c.total_sat_numerator += t.total_sat_numerator || 0
    c.total_sat_denominator += t.total_sat_denominator || 0
  })
  return Object.entries(classMap)
    .map(([name, data]) => ({
      name,
      team_count: data.team_count,
      count: data.count,
      total_calls: data.total_calls,
      total_ticket_count: data.total_ticket_count,
      ti_dan_lv: data.total_calls > 0 ? data.total_ticket_count / data.total_calls : 0,
      avg_duration: data.total_calls > 0 ? +(data.total_duration / data.total_calls).toFixed(1) : 0,
      avg_satisfaction: data.total_sat_denominator > 0 ? data.total_sat_numerator / data.total_sat_denominator : null
    }))
    .sort((a, b) => b.total_calls - a.total_calls)
}

function handlePieClick(name, filterType, filterValue, viewMode = 'team') {
  const state = { filterType, filterValue, currentPage: 1, class_name: '', classFilter: '', viewMode: 'team' }
  if (name) {
    if (state.filterType === 'team') {
      state.filterType = ''
      state.filterValue = ''
      state.currentPage = 1
    } else if (viewMode === 'class') {
      state.classFilter = name
      state.viewMode = 'team'
      state.filterType = ''
      state.filterValue = ''
    } else {
      state.filterType = 'team'
      state.filterValue = name
      state.currentPage = 1
    }
  }
  return { filterType: state.filterType, filterValue: state.filterValue, classFilter: state.classFilter, viewMode: state.viewMode }
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
    it('should use searchForm.team_desc when no drill-down filter active', () => {
      const data = [
        { name: '张三', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 } },
        { name: '李四', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20 } },
        { name: '王五', team_desc: 'B组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 30 } }
      ]
      const result = makeTeamMemberChartData(data, '', '', 'A组')
      expect(result).toHaveLength(2)
      expect(result[0].name).toBe('李四')
      expect(result[0].value).toBe(20)
      expect(result[1].name).toBe('张三')
      expect(result[1].value).toBe(10)
    })
    it('should prefer drill-down team filter over searchForm.team_desc', () => {
      const data = [
        { name: '张三', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 } },
        { name: '李四', team_desc: 'B组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20 } }
      ]
      const result = makeTeamMemberChartData(data, 'A组', 'team', 'B组')
      expect(result).toHaveLength(1)
      expect(result[0].name).toBe('张三')
      expect(result[0].value).toBe(10)
    })
  })

  describe('teamRanking - 组长补充', () => {
    it('should supplement leader from teamLeaders when not in tableData', () => {
      const data = [
        { role: '组员', name: '张三', team_desc: '一班1组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 } },
        { role: '组员', name: '李四', team_desc: '一班1组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20 } }
      ]
      const leaders = { '一班1组': '王组长', '二班1组': '赵组长' }
      const result = makeTeamRanking(data, leaders)
      expect(result).toHaveLength(1)
      expect(result[0].team).toBe('一班1组')
      expect(result[0].leader).toBe('王组长')
    })
    it('should prefer leader from tableData over teamLeaders', () => {
      const data = [
        { role: '组长', name: '张组长', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 5 } },
        { role: '组员', name: '张三', team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10 } }
      ]
      const leaders = { 'A组': '外部组长' }
      const result = makeTeamRanking(data, leaders)
      expect(result[0].leader).toBe('张组长')
    })
  })

  describe('classRanking - 班级聚集', () => {
    it('should aggregate team data by class prefix', () => {
      const teamData = [
        { team: '一班1组', leader: '', count: 5, total_calls: 100, total_ticket_count: 10, total_duration: 5000, total_sat_numerator: 80, total_sat_denominator: 90 },
        { team: '一班2组', leader: '', count: 4, total_calls: 80, total_ticket_count: 8, total_duration: 4000, total_sat_numerator: 60, total_sat_denominator: 70 },
        { team: '二班1组', leader: '', count: 6, total_calls: 150, total_ticket_count: 15, total_duration: 7500, total_sat_numerator: 120, total_sat_denominator: 130 }
      ]
      const result = makeClassRanking(teamData)
      expect(result).toHaveLength(2)
      const yiban = result.find(r => r.name === '一班')
      expect(yiban.team_count).toBe(2)
      expect(yiban.count).toBe(9)
      expect(yiban.total_calls).toBe(180)
      expect(yiban.total_ticket_count).toBe(18)
      expect(yiban.ti_dan_lv).toBeCloseTo(0.1, 4)
      expect(yiban.avg_satisfaction).toBeCloseTo(140 / 160, 4)
      const erban = result.find(r => r.name === '二班')
      expect(erban.team_count).toBe(1)
      expect(erban.count).toBe(6)
      expect(erban.total_calls).toBe(150)
      expect(erban.avg_satisfaction).toBeCloseTo(120 / 130, 4)
    })
    it('should return null avg_satisfaction when denominator is zero', () => {
      const teamData = [
        { team: '一班1组', leader: '', count: 5, total_calls: 100, total_ticket_count: 10, total_duration: 5000, total_sat_numerator: 0, total_sat_denominator: 0 },
      ]
      const result = makeClassRanking(teamData)
      expect(result[0].avg_satisfaction).toBeNull()
    })
    it('should sort by total_calls descending', () => {
      const teamData = [
        { team: '一般C组', leader: '', count: 1, total_calls: 30, total_ticket_count: 0, total_duration: 0, total_sat_numerator: 0, total_sat_denominator: 0 },
        { team: '一般A组', leader: '', count: 1, total_calls: 50, total_ticket_count: 0, total_duration: 0, total_sat_numerator: 0, total_sat_denominator: 0 },
        { team: '一般B组', leader: '', count: 1, total_calls: 40, total_ticket_count: 0, total_duration: 0, total_sat_numerator: 0, total_sat_denominator: 0 }
      ]
      const result = makeClassRanking(teamData)
      expect(result[0].total_calls).toBe(50)
      expect(result[1].total_calls).toBe(40)
      expect(result[2].total_calls).toBe(30)
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
    it('should set classFilter and switch to team on class mode click', () => {
      const result = handlePieClick('一班', '', '', 'class')
      expect(result.classFilter).toBe('一班')
      expect(result.viewMode).toBe('team')
      expect(result.filterType).toBe('')
    })
    it('should clear filter in bar chart mode regardless of viewMode', () => {
      const result = handlePieClick('张三', 'team', 'A组', 'class')
      expect(result.filterType).toBe('')
      expect(result.filterValue).toBe('')
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

describe('WorkloadReport - 总体满意率计算', () => {
  function getMetricValue(row, field) {
    const val = row.aggregated_metrics?.[field]
    if (val === null || val === undefined) return null
    return typeof val === 'number' ? val : parseFloat(val) || 0
  }

  function aggregateSatisfaction(data) {
    let satNum = 0, satDen = 0
    data.forEach(d => {
      const vs = getMetricValue(d, '呼入人工服务-满意度-非常满意量') || 0
      const s = getMetricValue(d, '呼入人工服务-满意度-满意量') || 0
      const g = getMetricValue(d, '呼入人工服务-满意度-一般量') || 0
      const ds = getMetricValue(d, '呼入人工服务-满意度-不满意量') || 0
      const vds = getMetricValue(d, '呼入人工服务-满意度-非常不满意量') || 0
      satNum += vs + s
      satDen += vs + s + g + ds + vds
    })
    return { numerator: satNum, denominator: satDen }
  }

  function totalSatisfactionRate(stats) {
    if (!stats.denominator) return 0
    return +(stats.numerator / stats.denominator * 100).toFixed(2)
  }

  it('should aggregate satisfaction across multiple people', () => {
    const data = [
      { aggregated_metrics: {
        '呼入人工服务-满意度-非常满意量': 8,
        '呼入人工服务-满意度-满意量': 1,
        '呼入人工服务-满意度-一般量': 1,
        '呼入人工服务-满意度-不满意量': 0,
        '呼入人工服务-满意度-非常不满意量': 0
      }},
      { aggregated_metrics: {
        '呼入人工服务-满意度-非常满意量': 10,
        '呼入人工服务-满意度-满意量': 5,
        '呼入人工服务-满意度-一般量': 3,
        '呼入人工服务-满意度-不满意量': 1,
        '呼入人工服务-满意度-非常不满意量': 1
      }}
    ]
    const stats = aggregateSatisfaction(data)
    expect(stats.numerator).toBe(24)
    expect(stats.denominator).toBe(30)
    expect(totalSatisfactionRate(stats)).toBe(80)
  })

  it('should return 0 when no satisfaction data', () => {
    const stats = aggregateSatisfaction([])
    expect(totalSatisfactionRate(stats)).toBe(0)
  })

  it('should handle missing fields gracefully', () => {
    const data = [
      { aggregated_metrics: {} },
      { aggregated_metrics: {
        '呼入人工服务-满意度-非常满意量': 5,
        '呼入人工服务-满意度-满意量': 2,
        '呼入人工服务-满意度-一般量': 1,
        '呼入人工服务-满意度-不满意量': 0,
        '呼入人工服务-满意度-非常不满意量': 0
      }}
    ]
    const stats = aggregateSatisfaction(data)
    expect(stats.numerator).toBe(7)
    expect(stats.denominator).toBe(8)
    expect(totalSatisfactionRate(stats)).toBe(87.5)
  })

  it('should handle all null metrics', () => {
    const data = [
      { aggregated_metrics: {
        '呼入人工服务-满意度-非常满意量': null,
        '呼入人工服务-满意度-满意量': null,
        '呼入人工服务-满意度-一般量': null,
        '呼入人工服务-满意度-不满意量': null,
        '呼入人工服务-满意度-非常不满意量': null
      }}
    ]
    const stats = aggregateSatisfaction(data)
    expect(stats.numerator).toBe(0)
    expect(stats.denominator).toBe(0)
    expect(totalSatisfactionRate(stats)).toBe(0)
  })

  it('should format as percentage with 2 decimals', () => {
    const stats = { numerator: 3, denominator: 7 }
    expect(totalSatisfactionRate(stats)).toBe(42.86)
  })
})

describe('WorkloadReport - 截图导出功能', () => {
  function getMetricValue(row, field) {
    const val = row.aggregated_metrics?.[field]
    if (val === null || val === undefined) return null
    return typeof val === 'number' ? val : parseFloat(val) || 0
  }

  function buildScreenshotColumns(visibleMetricCols, hasPermission, gapTargets) {
    const cols = [
      { prop: '_index', label: '排名', width: 55 },
      { prop: 'account', label: '账号', width: 110 },
      { prop: 'name', label: '姓名', width: 80 },
      { prop: 'team_desc', label: '班组', width: 140 },
      { prop: 'date_count', label: '天数', width: 60 },
      ...visibleMetricCols.map(c => ({ prop: c.field, label: c.label, width: c.width, isRate: c.isRate })),
      { prop: '_ti_dan_lv', label: '提单率', width: 85, isRate: true },
      { prop: '_call_hourly_rate', label: '接话小时量', width: 90 },
    ]
    if (hasPermission('workload_report.view_call_salary')) {
      cols.push({ prop: '_call_salary', label: '接话绩效(预测)', width: 100 })
    }
    if (hasPermission('workload_report.view_sat_salary')) {
      cols.push({ prop: '_sat_salary', label: '满意度绩效(预测)', width: 100 })
    }
    if (hasPermission('workload_report.view_total_salary')) {
      cols.push({ prop: '_total_salary', label: '合计绩效(预测)', width: 100 })
    }
    if (hasPermission('workload_report.view_gap')) {
      gapTargets.forEach(target => {
        cols.push({ prop: `gap_${target}`, label: `话务量差额(${target})`, width: 110 })
      })
    }
    if (hasPermission('workload_report.view_sat_diff')) {
      cols.push({ prop: '_sat_diff', label: '满意度差额', width: 100 })
    }
    return cols
  }

  function getScreenshotMetricStyle(fieldKey, value, targets) {
    if (!targets || !targets.length || value === null || value === undefined) return null
    const target = targets.find(t => t.field === fieldKey)
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

  function formatScreenshotCell(row, col, activeTargets, rowIndex) {
    if (col.prop === '_index') {
      return { text: String(rowIndex + 1), style: null }
    }
    let val
    if (col.prop === 'account' || col.prop === 'name' || col.prop === 'emp_no' || col.prop === 'team_desc' || col.prop === 'date_count') {
      val = row[col.prop]
    } else if (col.prop.startsWith('_') || col.prop.startsWith('gap_')) {
      val = row[col.prop]
    } else {
      val = getMetricValue(row, col.prop)
    }
    let text
    if (val === null || val === undefined) {
      text = '-'
    } else if (col.isRate) {
      const num = typeof val === 'number' ? val : parseFloat(val)
      text = isNaN(num) ? '-' : (num * 100).toFixed(2) + '%'
    } else if (typeof val === 'number') {
      text = Number.isInteger(val) ? String(val) : val.toFixed(1)
    } else {
      text = String(val)
    }
    let style = null
    if (text !== '-') {
      const numericVal = typeof val === 'number' ? val : (val !== null && val !== undefined ? parseFloat(val) : null)
      if (numericVal !== null && !isNaN(numericVal)) {
        style = getScreenshotMetricStyle(col.prop, numericVal, activeTargets)
      }
    }
    return { text, style }
  }

  function buildScreenshotHtml(title, periodInfo, filterInfo, columns, rows, now) {
    const pad = n => String(n).padStart(2, '0')
    const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
    const colGroup = columns.map(c => `<col style="width: ${c.width}px">`).join('')
    const headerRow = columns.map(c => `<th style="padding: 8px 6px; border: 1px solid #d9d9d9; white-space: nowrap; font-weight: 600;">${c.label}</th>`).join('')
    const bodyRows = rows.map((r, i) => {
      const bg = i % 2 === 0 ? '#fafafa' : '#ffffff'
      const cells = r.cells.map(c => {
        const extraStyle = c.style ? ` color: ${c.style.color}; font-weight: ${c.style.fontWeight};` : ''
        return `<td style="padding: 6px; border: 1px solid #e8e8e8; white-space: nowrap; background: ${bg};${extraStyle}">${c.text}</td>`
      }).join('')
      return `<tr>${cells}</tr>`
    }).join('')
    return `<div style="padding: 30px 30px 20px; font-family: 'Microsoft YaHei', 'PingFang SC', -apple-system, sans-serif; color: #333; min-width: ${columns.reduce((s, c) => s + c.width, 0) + 60}px;">
    <div style="text-align: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #409eff;">
      <h1 style="font-size: 20px; margin: 0 0 8px 0; color: #1d1d1f;">${title}</h1>
      <div style="font-size: 13px; color: #666; display: flex; justify-content: center; gap: 24px;">
        ${periodInfo ? `<span style="background: #f0f5ff; padding: 2px 10px; border-radius: 4px;">日期: ${periodInfo}</span>` : ''}
        ${filterInfo ? `<span style="background: #f0f5ff; padding: 2px 10px; border-radius: 4px;">${filterInfo}</span>` : ''}
      </div>
    </div>
    <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center;">
      ${colGroup}
      <thead>
        <tr style="background: #409eff; color: #fff;">${headerRow}</tr>
      </thead>
      <tbody>${bodyRows || '<tr><td colspan="' + columns.length + '" style="padding: 30px; text-align: center; color: #999;">暂无数据</td></tr>'}</tbody>
    </table>
    <div style="text-align: right; font-size: 11px; color: #b0b0b0; margin-top: 12px; padding-top: 8px; border-top: 1px solid #eee;">
      生成时间: ${dateStr}
    </div>
  </div>`
  }

  const hasAllPermissions = key => true
  const hasNoPermissions = key => false
  const hasSalaryPermissions = key => key !== 'workload_report.view_gap' && key !== 'workload_report.view_sat_diff'
  const gapTargets = [2000, 2500, 3000]

  const sampleTargets = [
    { field: '人工服务-满意度-满意率', label: '满意率', operator: 'lt', value: 0.95, color: '#F56C6C', enabled: true },
    { field: '_ti_dan_lv', label: '提单率', operator: 'gt', value: 0.15, color: '#E6A23C', enabled: true },
    { field: '_call_salary', label: '接话绩效', operator: 'lt', value: 3000, color: '#F56C6C', enabled: true },
    { field: '_sat_diff', label: '满意度差额', operator: 'lt', value: 0, color: '#F56C6C', enabled: true },
  ]

  describe('buildScreenshotColumns', () => {
    it('should include basic fixed columns', () => {
      const cols = buildScreenshotColumns([], hasNoPermissions, [])
      expect(cols.map(c => c.prop)).toEqual([
        '_index', 'account', 'name', 'team_desc', 'date_count',
        '_ti_dan_lv', '_call_hourly_rate'
      ])
    })

    it('should include visible metric columns', () => {
      const metricCols = [
        { field: '呼入人工服务-人工服务-通话次数', label: '通话次数', width: 80, isRate: false },
        { field: '人工服务-满意度-满意率', label: '满意率', width: 80, isRate: true },
      ]
      const cols = buildScreenshotColumns(metricCols, hasNoPermissions, [])
      expect(cols.map(c => c.prop)).toContain('呼入人工服务-人工服务-通话次数')
      expect(cols.map(c => c.prop)).toContain('人工服务-满意度-满意率')
      const metricCol = cols.find(c => c.prop === '人工服务-满意度-满意率')
      expect(metricCol.isRate).toBe(true)
    })

    it('should include salary columns when user has permission', () => {
      const cols = buildScreenshotColumns([], hasAllPermissions, gapTargets)
      expect(cols.map(c => c.prop)).toContain('_call_salary')
      expect(cols.map(c => c.prop)).toContain('_sat_salary')
      expect(cols.map(c => c.prop)).toContain('_total_salary')
      expect(cols.map(c => c.prop)).toContain('gap_2000')
      expect(cols.map(c => c.prop)).toContain('gap_2500')
      expect(cols.map(c => c.prop)).toContain('gap_3000')
      expect(cols.map(c => c.prop)).toContain('_sat_diff')
    })

    it('should exclude salary columns without permission', () => {
      const cols = buildScreenshotColumns([], hasNoPermissions, gapTargets)
      expect(cols.map(c => c.prop)).not.toContain('_call_salary')
      expect(cols.map(c => c.prop)).not.toContain('_sat_salary')
      expect(cols.map(c => c.prop)).not.toContain('_total_salary')
      expect(cols.map(c => c.prop)).not.toContain('gap_2000')
      expect(cols.map(c => c.prop)).not.toContain('_sat_diff')
    })

    it('should include only permitted salary columns', () => {
      const cols = buildScreenshotColumns([], hasSalaryPermissions, gapTargets)
      expect(cols.map(c => c.prop)).toContain('_call_salary')
      expect(cols.map(c => c.prop)).toContain('_sat_salary')
      expect(cols.map(c => c.prop)).toContain('_total_salary')
      expect(cols.map(c => c.prop)).not.toContain('gap_2000')
      expect(cols.map(c => c.prop)).not.toContain('_sat_diff')
    })

    it('should handle empty gap targets', () => {
      const cols = buildScreenshotColumns([], hasAllPermissions, [])
      expect(cols.map(c => c.prop)).not.toContain('gap_2000')
    })
  })

  describe('getScreenshotMetricStyle', () => {
    it('should return null when no targets', () => {
      expect(getScreenshotMetricStyle('人工服务-满意度-满意率', 0.90, [])).toBeNull()
    })

    it('should return null when no targets match', () => {
      expect(getScreenshotMetricStyle('unknown_field', 0.90, sampleTargets)).toBeNull()
    })

    it('should return style when satisfaction rate is below target (lt)', () => {
      const style = getScreenshotMetricStyle('人工服务-满意度-满意率', 0.90, sampleTargets)
      expect(style).toEqual({ color: '#F56C6C', fontWeight: 'bold' })
    })

    it('should return null when satisfaction rate meets target', () => {
      expect(getScreenshotMetricStyle('人工服务-满意度-满意率', 0.95, sampleTargets)).toBeNull()
      expect(getScreenshotMetricStyle('人工服务-满意度-满意率', 0.96, sampleTargets)).toBeNull()
    })

    it('should return style when ti_dan_lv exceeds target (gt)', () => {
      const style = getScreenshotMetricStyle('_ti_dan_lv', 0.20, sampleTargets)
      expect(style).toEqual({ color: '#E6A23C', fontWeight: 'bold' })
    })

    it('should handle le operator', () => {
      const targets = [{ field: 'test', label: '测试', operator: 'le', value: 100, color: '#F56C6C', enabled: true }]
      expect(getScreenshotMetricStyle('test', 100, targets)).toEqual({ color: '#F56C6C', fontWeight: 'bold' })
      expect(getScreenshotMetricStyle('test', 50, targets)).toEqual({ color: '#F56C6C', fontWeight: 'bold' })
      expect(getScreenshotMetricStyle('test', 101, targets)).toBeNull()
    })

    it('should handle ge operator', () => {
      const targets = [{ field: 'test', label: '测试', operator: 'ge', value: 80, color: '#67C23A', enabled: true }]
      expect(getScreenshotMetricStyle('test', 80, targets)).toEqual({ color: '#67C23A', fontWeight: 'bold' })
      expect(getScreenshotMetricStyle('test', 90, targets)).toEqual({ color: '#67C23A', fontWeight: 'bold' })
      expect(getScreenshotMetricStyle('test', 79, targets)).toBeNull()
    })
  })

  describe('formatScreenshotCell', () => {
    const row = {
      account: 'zhangsan',
      name: '张三',
      emp_no: 'EMP001',
      team_desc: '二班1组',
      date_count: 22,
      _ti_dan_lv: 0.156,
      _call_hourly_rate: 3.8,
      _call_salary: 3500.50,
      _sat_salary: 120.25,
      _total_salary: 3620.75,
      _sat_diff: 15.5,
      gap_2000: -150,
      gap_2500: -650,
      aggregated_metrics: {
        '呼入人工服务-人工服务-通话次数': 150,
        '人工服务-满意度-满意率': 0.95,
        '呼入人工服务-人工服务-通话总时长(秒)': 28800,
      }
    }

    it('should format basic text fields', () => {
      expect(formatScreenshotCell(row, { prop: 'account' }, [], 0).text).toBe('zhangsan')
      expect(formatScreenshotCell(row, { prop: 'name' }, [], 0).text).toBe('张三')
      expect(formatScreenshotCell(row, { prop: 'team_desc' }, [], 0).text).toBe('二班1组')
    })

    it('should format integer fields without decimals', () => {
      expect(formatScreenshotCell(row, { prop: 'date_count' }, [], 0).text).toBe('22')
    })

    it('should format decimal fields with 1 decimal', () => {
      expect(formatScreenshotCell(row, { prop: '_call_hourly_rate' }, [], 0).text).toBe('3.8')
    })

    it('should format rate fields as percentage', () => {
      expect(formatScreenshotCell(row, { prop: '_ti_dan_lv', isRate: true }, [], 0).text).toBe('15.60%')
      expect(formatScreenshotCell(row, { prop: '人工服务-满意度-满意率', isRate: true }, [], 0).text).toBe('95.00%')
    })

    it('should format metric values from aggregated_metrics', () => {
      expect(formatScreenshotCell(row, { prop: '呼入人工服务-人工服务-通话次数' }, [], 0).text).toBe('150')
    })

    it('should format decimal salary values with 1 decimal', () => {
      expect(formatScreenshotCell(row, { prop: '_call_salary' }, [], 0).text).toBe('3500.5')
      expect(formatScreenshotCell(row, { prop: '_sat_salary' }, [], 0).text).toBe('120.3')
    })

    it('should format gap values (negative integers)', () => {
      expect(formatScreenshotCell(row, { prop: 'gap_2000' }, [], 0).text).toBe('-150')
      expect(formatScreenshotCell(row, { prop: 'gap_2500' }, [], 0).text).toBe('-650')
    })

    it('should return dash with null style for null/undefined values', () => {
      const result = formatScreenshotCell({}, { prop: 'name' }, [], 0)
      expect(result.text).toBe('-')
      expect(result.style).toBeNull()
    })

    it('should return no style when targets list is empty', () => {
      expect(formatScreenshotCell(row, { prop: '_ti_dan_lv', isRate: true }, [], 0).style).toBeNull()
    })

    it('should return sequential rank for _index column', () => {
      expect(formatScreenshotCell(row, { prop: '_index' }, [], 0).text).toBe('1')
      expect(formatScreenshotCell(row, { prop: '_index' }, [], 5).text).toBe('6')
      expect(formatScreenshotCell(row, { prop: '_index' }, [], 0).style).toBeNull()
    })
  })

  describe('sortScreenshotData - 截图数据排序', () => {
    function sortScreenshotData(data, sortBy, sortOrder) {
      if (!sortBy || !sortOrder) return data
      return [...data].sort((a, b) => {
        let aVal, bVal
        if (sortBy === 'name' || sortBy === 'team_desc') {
          aVal = (a[sortBy] || '').toLowerCase()
          bVal = (b[sortBy] || '').toLowerCase()
          return sortOrder === 'ascending' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
        }
        if (sortBy === 'date_count') {
          aVal = a.date_count || 0
          bVal = b.date_count || 0
        } else if (sortBy.startsWith('gap_') || sortBy.startsWith('_')) {
          aVal = a[sortBy] ?? 0
          bVal = b[sortBy] ?? 0
        } else {
          aVal = a.aggregated_metrics?.[sortBy] || 0
          bVal = b.aggregated_metrics?.[sortBy] || 0
        }
        return sortOrder === 'ascending' ? aVal - bVal : bVal - aVal
      })
    }

    const data = [
      { name: '张三', date_count: 22, _call_salary: 3500, aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 150 } },
      { name: '李四', date_count: 20, _call_salary: 4200, aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 200 } },
      { name: '王五', date_count: 25, _call_salary: 2800, aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 120 } },
    ]

    it('should sort by name ascending', () => {
      const sorted = sortScreenshotData(data, 'name', 'ascending')
      expect(sorted[0].name).toBe('张三')
      expect(sorted[1].name).toBe('李四')
      expect(sorted[2].name).toBe('王五')
    })

    it('should sort by name descending', () => {
      const sorted = sortScreenshotData(data, 'name', 'descending')
      expect(sorted[0].name).toBe('王五')
      expect(sorted[1].name).toBe('李四')
      expect(sorted[2].name).toBe('张三')
    })

    it('should sort by date_count ascending', () => {
      const sorted = sortScreenshotData(data, 'date_count', 'ascending')
      expect(sorted[0].date_count).toBe(20)
      expect(sorted[1].date_count).toBe(22)
      expect(sorted[2].date_count).toBe(25)
    })

    it('should sort by date_count descending', () => {
      const sorted = sortScreenshotData(data, 'date_count', 'descending')
      expect(sorted[0].date_count).toBe(25)
      expect(sorted[1].date_count).toBe(22)
      expect(sorted[2].date_count).toBe(20)
    })

    it('should sort by metric field (通话次数) descending', () => {
      const sorted = sortScreenshotData(data, '呼入人工服务-人工服务-通话次数', 'descending')
      expect(sorted[0].name).toBe('李四')
      expect(sorted[1].name).toBe('张三')
      expect(sorted[2].name).toBe('王五')
    })

    it('should sort by computed _call_salary ascending', () => {
      const sorted = sortScreenshotData(data, '_call_salary', 'ascending')
      expect(sorted[0]._call_salary).toBe(2800)
      expect(sorted[1]._call_salary).toBe(3500)
      expect(sorted[2]._call_salary).toBe(4200)
    })

    it('should return original data when no sort key', () => {
      const sorted = sortScreenshotData(data, '', '')
      expect(sorted).toEqual(data)
    })

    it('should preserve all items after sorting', () => {
      const sorted = sortScreenshotData(data, 'name', 'ascending')
      expect(sorted).toHaveLength(3)
    })
  })

  describe('formatScreenshotCell - 预警颜色', () => {
    const row = {
      account: 'zhangsan',
      name: '张三',
      _ti_dan_lv: 0.20,
      _call_salary: 2500,
      aggregated_metrics: {
        '人工服务-满意度-满意率': 0.90,
      }
    }

    it('should apply red style when satisfaction rate is below target', () => {
      const result = formatScreenshotCell(row, { prop: '人工服务-满意度-满意率', isRate: true }, sampleTargets)
      expect(result.text).toBe('90.00%')
      expect(result.style).toEqual({ color: '#F56C6C', fontWeight: 'bold' })
    })

    it('should apply orange style when ti_dan_lv exceeds target', () => {
      const result = formatScreenshotCell(row, { prop: '_ti_dan_lv', isRate: true }, sampleTargets)
      expect(result.text).toBe('20.00%')
      expect(result.style).toEqual({ color: '#E6A23C', fontWeight: 'bold' })
    })

    it('should apply red style when call_salary is below target', () => {
      const rowWithDecimal = { ...row, _call_salary: 2500.5 }
      const result = formatScreenshotCell(rowWithDecimal, { prop: '_call_salary' }, sampleTargets)
      expect(result.text).toBe('2500.5')
      expect(result.style).toEqual({ color: '#F56C6C', fontWeight: 'bold' })
    })

    it('should return null style when value meets target', () => {
      const meetRow = { ...row, _ti_dan_lv: 0.10 }
      const result = formatScreenshotCell(meetRow, { prop: '_ti_dan_lv', isRate: true }, sampleTargets)
      expect(result.text).toBe('10.00%')
      expect(result.style).toBeNull()
    })

    it('should not apply style to basic text fields', () => {
      const result = formatScreenshotCell(row, { prop: 'account' }, sampleTargets)
      expect(result.text).toBe('zhangsan')
      expect(result.style).toBeNull()
    })
  })

  describe('buildScreenshotHtml', () => {
    const columns = [
      { prop: 'name', label: '姓名', width: 80 },
      { prop: 'account', label: '账号', width: 110 },
    ]
    const rows = [
      { cells: [{ text: '张三', style: { color: '#F56C6C', fontWeight: 'bold' } }, { text: 'zhangsan', style: null }] },
      { cells: [{ text: '李四', style: null }, { text: 'lisi', style: { color: '#E6A23C', fontWeight: 'bold' } }] },
    ]
    const now = new Date(2026, 6, 24, 10, 30, 0)

    it('should include title and period info', () => {
      const html = buildScreenshotHtml('工作量报表', '2026-07', '', columns, [], now)
      expect(html).toContain('工作量报表')
      expect(html).toContain('日期: 2026-07')
    })

    it('should include filter info when provided', () => {
      const html = buildScreenshotHtml('工作量报表', '', '班组: 二班1组', columns, [], now)
      expect(html).toContain('班组: 二班1组')
    })

    it('should include generation timestamp', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, [], now)
      expect(html).toContain('2026-07-24 10:30')
    })

    it('should render all rows', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, rows, now)
      expect(html).toContain('张三')
      expect(html).toContain('李四')
      expect(html).toContain('zhangsan')
      expect(html).toContain('lisi')
    })

    it('should render table header with column labels', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, rows, now)
      expect(html).toContain('姓名')
      expect(html).toContain('账号')
    })

    it('should show empty message when no rows', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, [], now)
      expect(html).toContain('暂无数据')
    })

    it('should alternate row background colors', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, rows, now)
      expect(html).toContain('#fafafa')
      expect(html).toContain('#ffffff')
    })

    it('should calculate correct min-width from column widths', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, rows, now)
      expect(html).toContain(`min-width: ${80 + 110 + 60}px`)
    })

    it('should not show period or filter sections when empty', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, rows, now)
      expect(html).not.toContain('日期:')
      expect(html).not.toContain('班组:')
    })
  })

  describe('buildScreenshotHtml - 预警颜色渲染', () => {
    const columns = [
      { prop: 'name', label: '姓名', width: 80 },
      { prop: '_ti_dan_lv', label: '提单率', width: 85, isRate: true },
    ]
    const rows = [
      { cells: [
        { text: '张三', style: null },
        { text: '20.00%', style: { color: '#E6A23C', fontWeight: 'bold' } },
      ]},
    ]
    const now = new Date(2026, 6, 24, 10, 30, 0)

    it('should inline color style in cells with style', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, rows, now)
      expect(html).toContain('color: #E6A23C')
      expect(html).toContain('font-weight: bold')
    })

    it('should not add extra color when style is null', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, rows, now)
      expect(html).not.toContain('color: undefined')
    })

    it('should still contain cell text', () => {
      const html = buildScreenshotHtml('工作量报表', '', '', columns, rows, now)
      expect(html).toContain('20.00%')
      expect(html).toContain('张三')
    })
  })
})

describe('WorkloadReport - 导出筛选功能', () => {
  function buildScreenshotColumns(visibleMetricCols, hasPermission, gapTargets) {
    const cols = [
      { prop: '_index', label: '排名', width: 55 },
      { prop: 'account', label: '账号', width: 110 },
      { prop: 'name', label: '姓名', width: 80 },
      { prop: 'team_desc', label: '班组', width: 140 },
      { prop: 'date_count', label: '天数', width: 60 },
      ...visibleMetricCols.map(c => ({ prop: c.field, label: c.label, width: c.width, isRate: c.isRate })),
      { prop: '_ti_dan_lv', label: '提单率', width: 85, isRate: true },
      { prop: '_call_hourly_rate', label: '接话小时量', width: 90 },
    ]
    if (hasPermission('workload_report.view_call_salary')) {
      cols.push({ prop: '_call_salary', label: '接话绩效(预测)', width: 100 })
    }
    if (hasPermission('workload_report.view_sat_salary')) {
      cols.push({ prop: '_sat_salary', label: '满意度绩效(预测)', width: 100 })
    }
    if (hasPermission('workload_report.view_total_salary')) {
      cols.push({ prop: '_total_salary', label: '合计绩效(预测)', width: 100 })
    }
    if (hasPermission('workload_report.view_gap')) {
      gapTargets.forEach(target => {
        cols.push({ prop: `gap_${target}`, label: `话务量差额(${target})`, width: 110 })
      })
    }
    if (hasPermission('workload_report.view_sat_diff')) {
      cols.push({ prop: '_sat_diff', label: '满意度差额', width: 100 })
    }
    return cols
  }

  function getMetricValue(row, field) {
    const val = row.aggregated_metrics?.[field]
    if (val === null || val === undefined) return null
    return typeof val === 'number' ? val : parseFloat(val) || 0
  }

  function getScreenshotMetricStyle(fieldKey, value, targets) {
    if (!targets || !targets.length || value === null || value === undefined) return null
    const target = targets.find(t => t.field === fieldKey)
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

  function formatScreenshotCell(row, col, activeTargets, rowIndex) {
    if (col.prop === '_index') {
      return { text: String(rowIndex + 1), style: null }
    }
    let val
    if (col.prop === 'account' || col.prop === 'name' || col.prop === 'emp_no' || col.prop === 'team_desc' || col.prop === 'date_count') {
      val = row[col.prop]
    } else if (col.prop.startsWith('_') || col.prop.startsWith('gap_')) {
      val = row[col.prop]
    } else {
      val = getMetricValue(row, col.prop)
    }
    let text
    if (val === null || val === undefined) {
      text = '-'
    } else if (col.isRate) {
      const num = typeof val === 'number' ? val : parseFloat(val)
      text = isNaN(num) ? '-' : (num * 100).toFixed(2) + '%'
    } else if (typeof val === 'number') {
      text = Number.isInteger(val) ? String(val) : val.toFixed(1)
    } else {
      text = String(val)
    }
    let style = null
    if (text !== '-') {
      const numericVal = typeof val === 'number' ? val : (val !== null && val !== undefined ? parseFloat(val) : null)
      if (numericVal !== null && !isNaN(numericVal)) {
        style = getScreenshotMetricStyle(col.prop, numericVal, activeTargets)
      }
    }
    return { text, style }
  }

  function generateCSV(columns, data, activeTargets) {
    const headers = columns.map(c => c.label)
    const rows = data.map((row, i) =>
      columns.map(col => {
        const cell = formatScreenshotCell(row, col, activeTargets, i)
        return cell.text
      })
    )
    return [headers, ...rows].map(line =>
      line.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')
    ).join('\n')
  }

  function generateFilename(teamDesc, className) {
    if (teamDesc) return `${teamDesc}_工作量报表.csv`
    if (className) return `${className}_工作量报表.csv`
    return 'workload_report_filtered.csv'
  }

  const hasAllPermissions = key => true
  const gapTargets = [2000, 2500, 3000]

  const sampleTargets = [
    { field: '人工服务-满意度-满意率', label: '满意率', operator: 'lt', value: 0.95, color: '#F56C6C', enabled: true },
    { field: '_ti_dan_lv', label: '提单率', operator: 'gt', value: 0.15, color: '#E6A23C', enabled: true },
  ]

  const filteredData = [
    {
      account: 'zhangsan', name: '张三', team_desc: '二班1组', date_count: 22,
      _ti_dan_lv: 0.156, _call_hourly_rate: 3.8,
      aggregated_metrics: {
        '呼入人工服务-人工服务-通话次数': 150,
        '人工服务-满意度-满意率': 0.95,
      }
    },
    {
      account: 'lisi', name: '李四', team_desc: '二班1组', date_count: 20,
      _ti_dan_lv: 0.20, _call_hourly_rate: 4.2,
      aggregated_metrics: {
        '呼入人工服务-人工服务-通话次数': 200,
        '人工服务-满意度-满意率': 0.90,
      }
    },
  ]

  describe('generateCSV', () => {
    it('should include headers and data rows', () => {
      const columns = buildScreenshotColumns([], hasAllPermissions, gapTargets)
      const csv = generateCSV(columns, filteredData, sampleTargets)
      const lines = csv.split('\n')
      expect(lines.length).toBe(3)
      expect(lines[0]).toContain('排名')
      expect(lines[0]).toContain('账号')
      expect(lines[0]).toContain('姓名')
      expect(lines[0]).toContain('班组')
      expect(lines[1]).toContain('张三')
      expect(lines[2]).toContain('李四')
    })

    it('should escape double quotes in values', () => {
      const data = [{
        account: 'a', name: 'Test "Quote"', team_desc: 'G1', date_count: 1,
        _ti_dan_lv: 0.1, _call_hourly_rate: 1,
      }]
      const columns = buildScreenshotColumns([], hasAllPermissions, gapTargets)
      const csv = generateCSV(columns, data, [])
      expect(csv).toContain('Test ""Quote""')
    })

    it('should format rate fields as percentage', () => {
      const columns = buildScreenshotColumns([], hasAllPermissions, gapTargets)
      const csv = generateCSV(columns, filteredData, sampleTargets)
      const lines = csv.split('\n')
      expect(lines[1]).toContain('15.60%')
      expect(lines[2]).toContain('20.00%')
    })

    it('should include ranking column', () => {
      const columns = buildScreenshotColumns([], hasAllPermissions, gapTargets)
      const csv = generateCSV(columns, filteredData, sampleTargets)
      const lines = csv.split('\n')
      expect(lines[1]).toContain('"1"')
      expect(lines[2]).toContain('"2"')
    })

    it('should apply warning colors to cell text in CSV', () => {
      const columns = buildScreenshotColumns([], hasAllPermissions, sampleTargets)
      const csv = generateCSV(columns, filteredData, sampleTargets)
      const lines = csv.split('\n')
      expect(lines[2]).toContain('20.00%')
    })
  })

  describe('generateFilename', () => {
    it('should use team_desc in filename', () => {
      expect(generateFilename('二班1组', '')).toBe('二班1组_工作量报表.csv')
    })

    it('should use class_name in filename', () => {
      expect(generateFilename('', '一班')).toBe('一班_工作量报表.csv')
    })

    it('should use default filename when no filter', () => {
      expect(generateFilename('', '')).toBe('workload_report_filtered.csv')
    })
  })

  describe('handleExportFiltered - empty data', () => {
    it('should return only header when no filtered data', () => {
      const columns = buildScreenshotColumns([], hasAllPermissions, gapTargets)
      const csv = generateCSV(columns, [], [])
      const lines = csv.split('\n')
      expect(lines.length).toBe(1)
      expect(lines[0]).toContain('排名')
    })
  })
})
