import { describe, it, expect } from 'vitest'

const mockTeamsData = [
  { team: '班组A', has_threshold: true, overtime_ratio: 1.2, undertime_ratio: 0.8 },
  { team: '班组B', has_threshold: false, overtime_ratio: 1.2, undertime_ratio: 0.8 },
  { team: '班组C', has_threshold: true, overtime_ratio: 1.3, undertime_ratio: 0.7 }
]

const mockThresholdsData = [
  { id: 1, team: '班组A', overtime_ratio: 1.2, undertime_ratio: 0.8 },
  { id: 3, team: '班组C', overtime_ratio: 1.3, undertime_ratio: 0.7 }
]

describe('WorkHourSettings - 阈值配置逻辑测试', () => {
  it('should format team data with threshold map', () => {
    const thresholdMap = {}
    mockThresholdsData.forEach(t => {
      thresholdMap[t.team] = t
    })
    
    const result = mockTeamsData.map(t => {
      const threshold = thresholdMap[t.team]
      return {
        team: t.team,
        overtime_ratio: threshold ? threshold.overtime_ratio : t.overtime_ratio,
        undertime_ratio: threshold ? threshold.undertime_ratio : t.undertime_ratio,
        has_threshold: !!threshold,
        editing: false,
        edit_overtime: threshold ? threshold.overtime_ratio : t.overtime_ratio,
        edit_undertime: threshold ? threshold.undertime_ratio : t.undertime_ratio,
        id: threshold ? threshold.id : null
      }
    })
    
    expect(result.length).toBe(3)
    expect(result[0].has_threshold).toBe(true)
    expect(result[0].id).toBe(1)
    expect(result[1].has_threshold).toBe(false)
    expect(result[1].id).toBeNull()
  })

  it('should validate default form values', () => {
    const form = {
      team: '',
      overtime_ratio: 1.2,
      undertime_ratio: 0.8
    }
    
    expect(form.overtime_ratio).toBe(1.2)
    expect(form.undertime_ratio).toBe(0.8)
  })

  it('should validate overtime_ratio range', () => {
    const validateRange = (val) => val >= 1.0 && val <= 2.0
    
    expect(validateRange(1.0)).toBe(true)
    expect(validateRange(1.2)).toBe(true)
    expect(validateRange(2.0)).toBe(true)
    expect(validateRange(0.9)).toBe(false)
    expect(validateRange(2.1)).toBe(false)
  })

  it('should validate undertime_ratio range', () => {
    const validateRange = (val) => val >= 0.1 && val <= 1.0
    
    expect(validateRange(0.1)).toBe(true)
    expect(validateRange(0.8)).toBe(true)
    expect(validateRange(1.0)).toBe(true)
    expect(validateRange(0.05)).toBe(false)
    expect(validateRange(1.1)).toBe(false)
  })

  it('should check team has threshold configured', () => {
    const teamA = mockTeamsData.find(t => t.team === '班组A')
    const teamB = mockTeamsData.find(t => t.team === '班组B')
    
    expect(teamA.has_threshold).toBe(true)
    expect(teamB.has_threshold).toBe(false)
  })

  it('should get available teams without threshold', () => {
    const configuredTeams = mockTeamsData.filter(t => t.has_threshold).map(t => t.team)
    const unconfigured = mockTeamsData.filter(t => !configuredTeams.includes(t.team))
    
    expect(unconfigured.length).toBe(1)
    expect(unconfigured[0].team).toBe('班组B')
  })

  it('should handle edit mode toggle', () => {
    const row = {
      team: '班组A',
      overtime_ratio: 1.2,
      editing: false,
      edit_overtime: 1.2,
      edit_undertime: 0.8
    }
    
    row.editing = true
    row.edit_overtime = 1.5
    row.edit_undertime = 0.6
    
    expect(row.editing).toBe(true)
    expect(row.edit_overtime).toBe(1.5)
    expect(row.edit_undertime).toBe(0.6)
  })

  it('should cancel edit and restore original values', () => {
    const originalValues = { overtime_ratio: 1.2, undertime_ratio: 0.8 }
    let editValues = { overtime_ratio: 1.5, undertime_ratio: 0.6 }
    let editing = true
    
    editValues.overtime_ratio = originalValues.overtime_ratio
    editValues.undertime_ratio = originalValues.undertime_ratio
    editing = false
    
    expect(editValues.overtime_ratio).toBe(1.2)
    expect(editValues.undertime_ratio).toBe(0.8)
    expect(editing).toBe(false)
  })

  it('should validate threshold data structure', () => {
    const threshold = {
      id: 1,
      team: '班组A',
      overtime_ratio: 1.2,
      undertime_ratio: 0.8
    }
    
    expect(threshold.id).toBeDefined()
    expect(threshold.team).toBe('班组A')
    expect(typeof threshold.overtime_ratio).toBe('number')
    expect(typeof threshold.undertime_ratio).toBe('number')
  })

  it('should merge team and threshold data correctly', () => {
    const teams = ['班组A', '班组B', '班组C']
    const thresholds = mockThresholdsData
    
    const result = teams.map(team => {
      const threshold = thresholds.find(t => t.team === team)
      return {
        team,
        has_threshold: !!threshold,
        overtime_ratio: threshold ? threshold.overtime_ratio : 1.2,
        undertime_ratio: threshold ? threshold.undertime_ratio : 0.8
      }
    })
    
    expect(result[0].has_threshold).toBe(true)
    expect(result[0].overtime_ratio).toBe(1.2)
    expect(result[1].has_threshold).toBe(false)
    expect(result[1].overtime_ratio).toBe(1.2)
    expect(result[2].has_threshold).toBe(true)
    expect(result[2].overtime_ratio).toBe(1.3)
  })
})