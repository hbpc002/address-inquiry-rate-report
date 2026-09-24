import { describe, it, expect } from 'vitest'

function calcTiDanLv(callCount, ticketCount) {
  if (callCount > 0) {
    return +(ticketCount / callCount * 100).toFixed(1)
  }
  return 0
}

function mergeTeamData(hoursData, prodData) {
  const prodMap = {}
  prodData.forEach(p => { prodMap[p.team] = p })
  return hoursData.slice(0, 10).map(h => {
    const p = prodMap[h.team]
    return {
      team: h.team,
      emp_count: h.emp_count,
      scheduled_hours: h.scheduled_hours,
      actual_hours: h.actual_hours,
      call_count: p?.call_count || 0,
      ticket_count: p?.ticket_count || 0,
      tiDanLv: p?.call_count > 0 ? +(p.ticket_count / p.call_count * 100).toFixed(1) : 0,
    }
  })
}

function getProductionByTeam(mergedData, teamName) {
  return mergedData.find(d => d.team === teamName)
}

function buildTeamXAxis(hoursData) {
  return {
    type: 'category',
    data: hoursData.map(d => d.team),
    axisLabel: { interval: 0, rotate: 28, margin: 8 },
  }
}

describe('dashboard - calcTiDanLv', () => {
  it('calculates ticket rate correctly', () => {
    expect(calcTiDanLv(100, 10)).toBe(10.0)
  })

  it('returns 0 when call count is 0', () => {
    expect(calcTiDanLv(0, 10)).toBe(0)
  })

  it('rounds to one decimal place', () => {
    expect(calcTiDanLv(3, 1)).toBe(33.3)
  })
})

describe('dashboard - mergeTeamData', () => {
  const hoursData = [
    { team: '热线一组', emp_count: 10, scheduled_hours: 800, actual_hours: 750 },
    { team: '热线二组', emp_count: 8, scheduled_hours: 640, actual_hours: 600 },
    { team: '投诉组', emp_count: 5, scheduled_hours: 400, actual_hours: 380 },
  ]
  const prodData = [
    { team: '热线一组', emp_count: 9, call_count: 5000, ticket_count: 250 },
    { team: '热线二组', emp_count: 7, call_count: 3000, ticket_count: 120 },
  ]

  it('merges hours and production data by team', () => {
    const merged = mergeTeamData(hoursData, prodData)
    expect(merged).toHaveLength(3)
  })

  it('preserves hours data for all teams', () => {
    const merged = mergeTeamData(hoursData, prodData)
    const team1 = getProductionByTeam(merged, '热线一组')
    expect(team1.scheduled_hours).toBe(800)
    expect(team1.actual_hours).toBe(750)
    expect(team1.emp_count).toBe(10)
  })

  it('merges production data for teams that have it', () => {
    const merged = mergeTeamData(hoursData, prodData)
    const team1 = getProductionByTeam(merged, '热线一组')
    expect(team1.call_count).toBe(5000)
    expect(team1.ticket_count).toBe(250)
    const team2 = getProductionByTeam(merged, '热线二组')
    expect(team2.call_count).toBe(3000)
    expect(team2.ticket_count).toBe(120)
  })

  it('defaults production to 0 for teams without workload data', () => {
    const merged = mergeTeamData(hoursData, prodData)
    const team3 = getProductionByTeam(merged, '投诉组')
    expect(team3.call_count).toBe(0)
    expect(team3.ticket_count).toBe(0)
    expect(team3.tiDanLv).toBe(0)
  })

  it('calculates tiDanLv correctly for merged teams', () => {
    const merged = mergeTeamData(hoursData, prodData)
    const team1 = getProductionByTeam(merged, '热线一组')
    expect(team1.tiDanLv).toBe(5.0)
    const team2 = getProductionByTeam(merged, '热线二组')
    expect(team2.tiDanLv).toBe(4.0)
  })

  it('limits to top 10 teams', () => {
    const manyHours = Array.from({ length: 15 }, (_, i) => ({
      team: `班组${i + 1}`, emp_count: 5, scheduled_hours: 400, actual_hours: 380,
    }))
    const merged = mergeTeamData(manyHours, [])
    expect(merged).toHaveLength(10)
  })
})

describe('dashboard - buildTeamXAxis', () => {
  const hoursData = [
    { team: '热线一组', emp_count: 10, scheduled_hours: 800, actual_hours: 750 },
    { team: '热线二组', emp_count: 8, scheduled_hours: 640, actual_hours: 600 },
    { team: '投诉组', emp_count: 5, scheduled_hours: 400, actual_hours: 380 },
  ]

  it('uses single-line team names as categories (no emp_count suffix)', () => {
    const axis = buildTeamXAxis(hoursData)
    expect(axis.data).toEqual(['热线一组', '热线二组', '投诉组'])
    expect(axis.data.every(d => !d.includes('\n'))).toBe(true)
  })

  it('forces interval 0 so no labels are auto-hidden', () => {
    const axis = buildTeamXAxis(hoursData)
    expect(axis.axisLabel.interval).toBe(0)
  })

  it('rotates labels to avoid overlap', () => {
    const axis = buildTeamXAxis(hoursData)
    expect(axis.axisLabel.rotate).toBe(28)
  })

  it('keeps every team visible regardless of count', () => {
    const many = Array.from({ length: 12 }, (_, i) => ({ team: `班组${i + 1}`, emp_count: 5 }))
    const axis = buildTeamXAxis(many)
    expect(axis.data).toHaveLength(12)
  })
})

// ---- 休息/示忙分析 helpers（与 Dashboard.vue 中逻辑一致）----

const STATE_FIELDS = {
  busy_count: '操作次数及时长-示忙次数',
  busy_seconds: '操作次数及时长-示忙时长(秒)',
  rest_count: '操作次数及时长-休息次数',
  rest_seconds: '操作次数及时长-休息时长(秒)',
}

function extractStatePerson(item) {
  const m = item.aggregated_metrics || {}
  const busyCount = m[STATE_FIELDS.busy_count] || 0
  const restCount = m[STATE_FIELDS.rest_count] || 0
  return {
    account: item.account,
    name: item.name,
    team_desc: item.team_desc,
    busy_count: busyCount,
    busy_hours: +(((m[STATE_FIELDS.busy_seconds] || 0) / 3600)).toFixed(2),
    rest_count: restCount,
    rest_hours: +(((m[STATE_FIELDS.rest_seconds] || 0) / 3600)).toFixed(2),
    freq: 1,
  }
}

function groupStateByTeam(persons) {
  const map = {}
  persons.forEach(p => {
    const team = p.team_desc || '未知班组'
    if (!map[team]) map[team] = { team, busy_count: 0, busy_hours: 0, rest_count: 0, rest_hours: 0, _people: new Set() }
    map[team].busy_count += p.busy_count
    map[team].busy_hours = +(map[team].busy_hours + p.busy_hours).toFixed(2)
    map[team].rest_count += p.rest_count
    map[team].rest_hours = +(map[team].rest_hours + p.rest_hours).toFixed(2)
    map[team]._people.add(p.account)
  })
  return Object.values(map).map(t => ({
    team: t.team,
    busy_count: t.busy_count,
    busy_hours: t.busy_hours,
    rest_count: t.rest_count,
    rest_hours: t.rest_hours,
    people: t._people.size,
    freq: t._people.size ? +(t.busy_count / t._people.size).toFixed(2) : 0,
  }))
}

function buildDailyStateSeries(data) {
  return [
    { name: '示忙次数', type: 'bar', data: data.map(d => d.busy_count) },
    { name: '休息次数', type: 'bar', data: data.map(d => d.rest_count) },
    { name: '示忙时长(h)', type: 'line', yAxisIndex: 1, data: data.map(d => +(d.busy_seconds / 3600).toFixed(2)) },
    { name: '休息时长(h)', type: 'line', yAxisIndex: 1, data: data.map(d => +(d.rest_seconds / 3600).toFixed(2)) },
  ]
}

function buildTeamStateSeries(teams, metric) {
  const busyData = teams.map(t => metric === 'count' ? t.busy_count : metric === 'duration' ? t.busy_hours : +(t.busy_count / (t.people || 1)).toFixed(2))
  const restData = teams.map(t => metric === 'count' ? t.rest_count : metric === 'duration' ? t.rest_hours : +(t.rest_count / (t.people || 1)).toFixed(2))
  return [
    { name: '示忙', type: 'bar', data: busyData.slice().reverse() },
    { name: '休息', type: 'bar', data: restData.slice().reverse() },
  ]
}

describe('dashboard - extractStatePerson', () => {
  const item = {
    account: 'STTR00001',
    name: '张三',
    team_desc: '热线一组',
    aggregated_metrics: {
      '操作次数及时长-示忙次数': 4,
      '操作次数及时长-示忙时长(秒)': 7200,
      '操作次数及时长-休息次数': 2,
      '操作次数及时长-休息时长(秒)': 1800,
    },
  }

  it('extracts counts and converts seconds to hours', () => {
    const p = extractStatePerson(item)
    expect(p.busy_count).toBe(4)
    expect(p.busy_hours).toBe(2.0)
    expect(p.rest_count).toBe(2)
    expect(p.rest_hours).toBe(0.5)
    expect(p.account).toBe('STTR00001')
    expect(p.team_desc).toBe('热线一组')
  })

  it('defaults missing metrics to 0', () => {
    const p = extractStatePerson({ account: 'A', name: 'N', team_desc: 'T', aggregated_metrics: {} })
    expect(p.busy_count).toBe(0)
    expect(p.busy_hours).toBe(0)
    expect(p.rest_count).toBe(0)
    expect(p.rest_hours).toBe(0)
  })

  it('handles null aggregated_metrics', () => {
    const p = extractStatePerson({ account: 'A', name: 'N', team_desc: 'T' })
    expect(p.busy_count).toBe(0)
    expect(p.rest_count).toBe(0)
  })
})

describe('dashboard - groupStateByTeam', () => {
  const persons = [
    { account: 'A1', name: '甲', team_desc: '一组', busy_count: 4, busy_hours: 2, rest_count: 2, rest_hours: 0.5 },
    { account: 'A2', name: '乙', team_desc: '一组', busy_count: 6, busy_hours: 1, rest_count: 1, rest_hours: 0.2 },
    { account: 'A3', name: '丙', team_desc: '二组', busy_count: 3, busy_hours: 0.5, rest_count: 0, rest_hours: 0 },
  ]

  it('groups persons by team and sums metrics', () => {
    const teams = groupStateByTeam(persons)
    expect(teams).toHaveLength(2)
    const t1 = teams.find(t => t.team === '一组')
    expect(t1.busy_count).toBe(10)
    expect(t1.busy_hours).toBe(3.0)
    expect(t1.rest_count).toBe(3)
    expect(t1.people).toBe(2)
  })

  it('computes freq as busy_count / unique people', () => {
    const teams = groupStateByTeam(persons)
    const t1 = teams.find(t => t.team === '一组')
    expect(t1.freq).toBe(5.0)
    const t2 = teams.find(t => t.team === '二组')
    expect(t2.freq).toBe(3.0)
  })

  it('uses 未知班组 when team_desc missing', () => {
    const teams = groupStateByTeam([{ account: 'X', name: 'X', team_desc: null, busy_count: 1, busy_hours: 0, rest_count: 0, rest_hours: 0 }])
    expect(teams[0].team).toBe('未知班组')
    expect(teams[0].freq).toBe(1)
  })

  it('returns empty array for no persons', () => {
    expect(groupStateByTeam([])).toEqual([])
  })
})

describe('dashboard - buildDailyStateSeries', () => {
  const data = [
    { date: '2026-06-28', busy_count: 10, busy_seconds: 10800, rest_count: 3, rest_seconds: 2400, people_count: 2, busy_freq: 5, rest_freq: 1.5 },
    { date: '2026-06-29', busy_count: 3, busy_seconds: 1800, rest_count: 0, rest_seconds: 0, people_count: 1, busy_freq: 3, rest_freq: 0 },
  ]

  it('builds 4 series: 2 count bars + 2 duration lines in hours', () => {
    const series = buildDailyStateSeries(data)
    expect(series).toHaveLength(4)
    expect(series[0].name).toBe('示忙次数')
    expect(series[0].type).toBe('bar')
    expect(series[0].data).toEqual([10, 3])
    expect(series[1].name).toBe('休息次数')
    expect(series[1].data).toEqual([3, 0])
    expect(series[2].name).toBe('示忙时长(h)')
    expect(series[2].type).toBe('line')
    expect(series[2].yAxisIndex).toBe(1)
    expect(series[2].data).toEqual([3.0, 0.5])
    expect(series[3].name).toBe('休息时长(h)')
    expect(series[3].data).toEqual([0.67, 0])
  })
})

describe('dashboard - buildTeamStateSeries', () => {
  const teams = [
    { team: '一组', busy_count: 10, busy_hours: 3, rest_count: 3, rest_hours: 0.7, people: 2 },
    { team: '二组', busy_count: 3, busy_hours: 0.5, rest_count: 0, rest_hours: 0, people: 1 },
  ]

  it('metric=count uses raw counts reversed for horizontal bar', () => {
    const series = buildTeamStateSeries(teams, 'count')
    expect(series[0].data).toEqual([3, 10])
    expect(series[1].data).toEqual([0, 3])
  })

  it('metric=duration uses hours reversed', () => {
    const series = buildTeamStateSeries(teams, 'duration')
    expect(series[0].data).toEqual([0.5, 3])
    expect(series[1].data).toEqual([0, 0.7])
  })

  it('metric=freq computes count/people reversed', () => {
    const series = buildTeamStateSeries(teams, 'freq')
    expect(series[0].data).toEqual([3.0, 5.0])
    expect(series[1].data).toEqual([0, 1.5])
  })
})
