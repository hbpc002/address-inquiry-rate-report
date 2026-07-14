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
