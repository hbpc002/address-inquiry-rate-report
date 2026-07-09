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
  const vals = data
    .map(d => getMetricValue(d, '呼入人工服务-人工服务-通话均长(秒)'))
    .filter(v => v !== null && v !== undefined)
  if (vals.length === 0) return 0
  const sum = vals.reduce((a, b) => a + b, 0)
  return Math.round(sum / vals.length * 10) / 10
}

function makeTeamRanking(data) {
  const teamMap = {}
  data.forEach(d => {
    const team = d.team_desc || '未知班组'
    if (!teamMap[team]) {
      teamMap[team] = { count: 0, total_calls: 0, total_duration: 0, total_satisfaction: 0, sat_count: 0, total_ticket_count: 0, total_outbound: 0 }
    }
    teamMap[team].count++
    teamMap[team].total_calls += getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    teamMap[team].total_ticket_count += getMetricValue(d, '呼入人工服务-工单-生成总量') || 0
    teamMap[team].total_outbound += getMetricValue(d, '呼出服务-人工呼出呼叫量') || 0
    const avgDur = getMetricValue(d, '呼入人工服务-人工服务-通话均长(秒)')
    if (avgDur !== null) teamMap[team].total_duration += avgDur
    const sat = getMetricValue(d, '人工服务-满意度-满意率')
    if (sat !== null) {
      teamMap[team].total_satisfaction += sat
      teamMap[team].sat_count++
    }
  })
  return Object.entries(teamMap)
    .map(([team, data]) => ({
      team,
      count: data.count,
      total_calls: data.total_calls,
      total_ticket_count: data.total_ticket_count,
      total_outbound: data.total_outbound,
      ti_dan_lv: data.total_calls > 0 ? data.total_ticket_count / data.total_calls : 0,
      avg_duration: data.count > 0 ? (data.total_duration / data.count).toFixed(1) : 0,
      avg_satisfaction: data.sat_count > 0 ? (data.total_satisfaction / data.sat_count) : null
    }))
    .sort((a, b) => b.total_calls - a.total_calls)
}

function makeTeamChartData(data) {
  const teamMap = {}
  data.forEach(d => {
    const team = d.team_desc || '未知班组'
    if (!teamMap[team]) {
      teamMap[team] = { value: 0, count: 0, totalDuration: 0, durCount: 0, totalTicket: 0 }
    }
    const t = teamMap[team]
    t.value += getMetricValue(d, '呼入人工服务-人工服务-通话次数') || 0
    t.count++
    t.totalTicket += getMetricValue(d, '呼入人工服务-工单-生成总量') || 0
    const avgDur = getMetricValue(d, '呼入人工服务-人工服务-通话均长(秒)')
    if (avgDur !== null) {
      t.totalDuration += avgDur
      t.durCount++
    }
  })
  return Object.entries(teamMap)
    .map(([name, data]) => ({
      name,
      value: Math.round(data.value),
      peopleCount: data.count,
      avgDuration: data.durCount > 0 ? (data.totalDuration / data.durCount).toFixed(1) : 0,
      totalTicket: Math.round(data.totalTicket),
      tiDanLv: data.value > 0 ? data.totalTicket / data.value : 0
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
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
    it('should compute average from 通话均长 values', () => {
      const data = [
        { aggregated_metrics: { '呼入人工服务-人工服务-通话均长(秒)': 180 } },
        { aggregated_metrics: { '呼入人工服务-人工服务-通话均长(秒)': 220 } },
        { aggregated_metrics: { '呼入人工服务-人工服务-通话均长(秒)': 200 } }
      ]
      expect(getAvgDuration(data)).toBe(200)
    })
    it('should skip null/undefined values', () => {
      const data = [
        { aggregated_metrics: { '呼入人工服务-人工服务-通话均长(秒)': 180 } },
        { aggregated_metrics: {} },
        { aggregated_metrics: { '呼入人工服务-人工服务-通话均长(秒)': null } }
      ]
      expect(getAvgDuration(data)).toBe(180)
    })
    it('should return 0 for empty data', () => {
      expect(getAvgDuration([])).toBe(0)
    })
    it('should return 0 when all values are null', () => {
      const data = [
        { aggregated_metrics: { '呼入人工服务-人工服务-通话均长(秒)': null } },
        { aggregated_metrics: {} }
      ]
      expect(getAvgDuration(data)).toBe(0)
    })
  })

  describe('teamRanking merge', () => {
    it('should aggregate team data with all required fields', () => {
      const data = [
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10, '呼入人工服务-人工服务-通话均长(秒)': 180, '人工服务-满意度-满意率': 0.95, '呼入人工服务-工单-生成总量': 5, '呼出服务-人工呼出呼叫量': 3 } },
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20, '呼入人工服务-人工服务-通话均长(秒)': 200, '人工服务-满意度-满意率': 0.90, '呼入人工服务-工单-生成总量': 8, '呼出服务-人工呼出呼叫量': 4 } },
        { team_desc: 'B组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 30, '呼入人工服务-人工服务-通话均长(秒)': 150, '人工服务-满意度-满意率': 0.85, '呼入人工服务-工单-生成总量': 12, '呼出服务-人工呼出呼叫量': 6 } }
      ]
      const result = makeTeamRanking(data)
      expect(result).toHaveLength(2)
      const teamA = result.find(r => r.team === 'A组')
      expect(teamA.count).toBe(2)
      expect(teamA.total_calls).toBe(30)
      expect(teamA.total_ticket_count).toBe(13)
      expect(teamA.total_outbound).toBe(7)
      expect(teamA.ti_dan_lv).toBeCloseTo(13 / 30, 4)
      expect(teamA.avg_duration).toBe('190.0')
      expect(teamA.avg_satisfaction).toBe(0.925)
      const teamB = result.find(r => r.team === 'B组')
      expect(teamB.count).toBe(1)
      expect(teamB.total_calls).toBe(30)
      expect(teamB.total_ticket_count).toBe(12)
      expect(teamB.total_outbound).toBe(6)
      expect(teamB.ti_dan_lv).toBeCloseTo(12 / 30, 4)
    })
    it('should handle unknown team_desc', () => {
      const data = [
        { aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 5 } }
      ]
      const result = makeTeamRanking(data)
      expect(result[0].team).toBe('未知班组')
      expect(result[0].total_ticket_count).toBe(0)
      expect(result[0].total_outbound).toBe(0)
      expect(result[0].ti_dan_lv).toBe(0)
    })
  })

  describe('teamChartData merge', () => {
    it('should aggregate team chart data with extra tooltip fields', () => {
      const data = [
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10, '呼入人工服务-人工服务-通话均长(秒)': 180, '呼入人工服务-工单-生成总量': 5 } },
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 20, '呼入人工服务-人工服务-通话均长(秒)': 200, '呼入人工服务-工单-生成总量': 8 } },
        { team_desc: 'B组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 30, '呼入人工服务-人工服务-通话均长(秒)': 150, '呼入人工服务-工单-生成总量': 12 } }
      ]
      const result = makeTeamChartData(data)
      expect(result).toHaveLength(2)
      const teamA = result.find(r => r.name === 'A组')
      expect(teamA.value).toBe(30)
      expect(teamA.peopleCount).toBe(2)
      expect(teamA.avgDuration).toBe('190.0')
      expect(teamA.totalTicket).toBe(13)
      expect(teamA.tiDanLv).toBeCloseTo(13 / 30, 4)
      const teamB = result.find(r => r.name === 'B组')
      expect(teamB.value).toBe(30)
      expect(teamB.peopleCount).toBe(1)
      expect(teamB.avgDuration).toBe('150.0')
      expect(teamB.totalTicket).toBe(12)
      expect(teamB.tiDanLv).toBeCloseTo(12 / 30, 4)
    })
    it('should handle null duration gracefully', () => {
      const data = [
        { team_desc: 'A组', aggregated_metrics: { '呼入人工服务-人工服务-通话次数': 10, '呼入人工服务-人工服务-通话均长(秒)': null, '呼入人工服务-工单-生成总量': 3 } },
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
