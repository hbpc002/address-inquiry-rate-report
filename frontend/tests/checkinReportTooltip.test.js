import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

describe('CheckinReport - 班组工时明细表列配置', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../src/views/CheckinReport.vue'), 'utf-8')
  const teamTableStart = source.indexOf('<el-table :data="teamMetricsRanking"')
  const teamTableEnd = source.indexOf('</el-table>', teamTableStart)
  const teamTableBlock = teamTableStart >= 0 && teamTableEnd > teamTableStart
    ? source.slice(teamTableStart, teamTableEnd)
    : ''

  it('班组工时明细表应删除通话时长/整理时长/培训扣除/晚签早退等 7 列', () => {
    expect(teamTableBlock).toBeTruthy()
    const removed = ['通话时长', '整理时长', '培训扣除(分)', '晚签人数', '晚签天数', '早退人数', '早退天数']
    removed.forEach(label => {
      expect(teamTableBlock.includes(label), `班组明细表不应再包含列: ${label}`).toBe(false)
    })
  })

  it('班组工时明细表应保留排名/班组/组长/人数/工时/遵时率/利用率/出勤率/占比列', () => {
    const kept = ['排名', '组长', '人数', '总工作时长', '总排班工时', '人均工作时长', '系统遵时率', '遵时率', '工时利用率', '班表出勤率', '占比']
    kept.forEach(label => {
      expect(teamTableBlock.includes(label), `班组明细表应保留列: ${label}`).toBe(true)
    })
  })
})

describe('CheckinReport - 已移除的员工排名图表', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../src/views/CheckinReport.vue'), 'utf-8')

  it('不再引用员工工时排名/员工签入次数排名图表及其点击处理器', () => {
    expect(source.includes('员工工时排名')).toBe(false)
    expect(source.includes('员工签入次数排名')).toBe(false)
    expect(source.includes('hoursChartOptions')).toBe(false)
    expect(source.includes('checkinCountOptions')).toBe(false)
    expect(source.includes('handleHoursChartClick')).toBe(false)
    expect(source.includes('handleCheckinChartClick')).toBe(false)
    expect(source.includes('chartType')).toBe(false)
  })
})

describe('CheckinReport - 班组工时明细表 (teamMetricsRanking)', () => {
  const mergedData = [
    {
      emp_no: 'E001', name: '张三', team: '班组A',
      total_hours: 85.5, scheduled_hours: 80.0,
      avg_punctuality_rate: 95.2, computed_punctuality_rate: 96.0,
      avg_utilization_rate: 70.0, avg_attendance_rate: 90.0,
      total_call_duration: 20.0, total_organize_duration: 5.0,
      training_minutes: 30, late_days: 1, late_minutes: 15, early_days: 0, early_minutes: 0
    },
    {
      emp_no: 'E002', name: '李四', team: '班组A',
      total_hours: 64.0, scheduled_hours: 72.0,
      avg_punctuality_rate: 98.0, computed_punctuality_rate: 99.0,
      avg_utilization_rate: 80.5, avg_attendance_rate: 95.0,
      total_call_duration: 30.0, total_organize_duration: 8.0,
      training_minutes: 10, late_days: 2, late_minutes: 45, early_days: 1, early_minutes: 20
    },
    {
      emp_no: 'E003', name: '王五', team: '班组B',
      total_hours: 80.0, scheduled_hours: 80.0,
      avg_punctuality_rate: 99.0, computed_punctuality_rate: 99.5,
      avg_utilization_rate: 85.0, avg_attendance_rate: 98.0,
      total_call_duration: 40.0, total_organize_duration: 10.0,
      training_minutes: 0, late_days: 0, late_minutes: 0, early_days: 2, early_minutes: 35
    }
  ]
  const teamLeaders = { 班组A: '张三', 班组B: '王五' }

  function buildTeamMetrics(rows) {
    const teamMap = {}
    rows.forEach(d => {
      const team = d.team || '未知班组'
      if (!teamMap[team]) {
        teamMap[team] = {
          count: 0, total_hours: 0, scheduled_hours: 0,
          avg_pun_sum: 0, avg_pun_n: 0, computed_sum: 0, computed_n: 0,
          util_sum: 0, util_n: 0, attend_sum: 0, attend_n: 0,
          total_call_duration: 0, total_organize_duration: 0, training_minutes: 0,
          late_people: 0, late_days: 0, early_people: 0, early_days: 0
        }
      }
      const t = teamMap[team]
      t.count++
      t.total_hours += d.total_hours
      t.scheduled_hours += d.scheduled_hours != null ? d.scheduled_hours : 0
      if (d.avg_punctuality_rate != null) { t.avg_pun_sum += d.avg_punctuality_rate; t.avg_pun_n++ }
      if (d.computed_punctuality_rate != null) { t.computed_sum += d.computed_punctuality_rate; t.computed_n++ }
      if (d.avg_utilization_rate != null) { t.util_sum += d.avg_utilization_rate; t.util_n++ }
      if (d.avg_attendance_rate != null) { t.attend_sum += d.avg_attendance_rate; t.attend_n++ }
      t.total_call_duration += d.total_call_duration || 0
      t.total_organize_duration += d.total_organize_duration || 0
      t.training_minutes += d.training_minutes || 0
      if ((d.late_days || 0) > 0) {
        t.late_people++
        t.late_days += d.late_days
      }
      if ((d.early_days || 0) > 0) {
        t.early_people++
        t.early_days += d.early_days
      }
    })
    return Object.entries(teamMap).map(([team, t]) => ({
      team,
      leader: teamLeaders[team] || '',
      count: t.count,
      total_hours: t.total_hours,
      scheduled_hours: t.scheduled_hours,
      avg_hours: t.count > 0 ? t.total_hours / t.count : 0,
      avg_punctuality_rate: t.avg_pun_n > 0 ? t.avg_pun_sum / t.avg_pun_n : null,
      computed_punctuality_rate: t.computed_n > 0 ? t.computed_sum / t.computed_n : null,
      avg_utilization_rate: t.util_n > 0 ? t.util_sum / t.util_n : null,
      avg_attendance_rate: t.attend_n > 0 ? t.attend_sum / t.attend_n : null,
      total_call_duration: t.total_call_duration,
      total_organize_duration: t.total_organize_duration,
      training_minutes: t.training_minutes,
      late_people: t.late_people,
      late_days: t.late_days,
      early_people: t.early_people,
      early_days: t.early_days
    })).sort((a, b) => b.total_hours - a.total_hours).slice(0, 8)
  }

  it('按总工作时长降序聚合班组', () => {
    const ranking = buildTeamMetrics(mergedData)
    expect(ranking.map(r => r.team)).toEqual(['班组A', '班组B'])
    expect(ranking[0].total_hours).toBe(149.5)
  })

  it('组长列从 teamLeaders 映射填充', () => {
    const ranking = buildTeamMetrics(mergedData)
    expect(ranking[0].leader).toBe('张三')
    expect(ranking[1].leader).toBe('王五')
  })

  it('加权平均系统遵时率与遵时率', () => {
    const ranking = buildTeamMetrics(mergedData)
    expect(ranking[0].computed_punctuality_rate).toBe((96.0 + 99.0) / 2)
    expect(ranking[0].avg_punctuality_rate).toBe((95.2 + 98.0) / 2)
  })

  it('晚签/早退人数与天数聚合正确', () => {
    const ranking = buildTeamMetrics(mergedData)
    expect(ranking[0].late_people).toBe(2)
    expect(ranking[0].late_days).toBe(3)
    expect(ranking[1].early_people).toBe(1)
    expect(ranking[1].early_days).toBe(2)
  })

  it('人均工时与总排班工时计算正确', () => {
    const ranking = buildTeamMetrics(mergedData)
    expect(ranking[0].avg_hours).toBe(149.5 / 2)
    expect(ranking[0].scheduled_hours).toBe(152.0)
  })

  it('top8 截断（超过 8 个班组时仅保留前 8）', () => {
    const rows = []
    for (let i = 0; i < 10; i++) {
      rows.push({ emp_no: 'E' + i, name: '员工' + i, team: '班组' + i, total_hours: 10 + i, scheduled_hours: 10, late_days: 0, early_days: 0 })
    }
    const ranking = buildTeamMetrics(rows)
    expect(ranking.length).toBe(8)
  })
})

describe('CheckinReport - 班组晚签/早退 tooltip 人名+累计分钟（两列同时显示）', () => {
  const mergedData = [
    { emp_no: 'E001', name: '张三', team: '班组A', late_days: 1, late_minutes: 20, early_days: 0, early_minutes: 0 },
    { emp_no: 'E002', name: '李四', team: '班组A', late_days: 2, late_minutes: 45, early_days: 1, early_minutes: 10 },
    { emp_no: 'E003', name: '王五', team: '班组B', late_days: 0, late_minutes: 0, early_days: 2, early_minutes: 35 }
  ]

  function buildLateEarlyMaps(rows) {
    const teamMap = {}
    const latePeopleMap = {}
    const earlyPeopleMap = {}
    rows.forEach(d => {
      const t = d.team || '未知班组'
      if (!teamMap[t]) teamMap[t] = { late: 0, early: 0 }
      if ((d.late_days || 0) > 0) {
        teamMap[t].late += 1
        if (!latePeopleMap[t]) latePeopleMap[t] = []
        latePeopleMap[t].push({ name: d.name, minutes: d.late_minutes || 0 })
      }
      if ((d.early_days || 0) > 0) {
        teamMap[t].early += 1
        if (!earlyPeopleMap[t]) earlyPeopleMap[t] = []
        earlyPeopleMap[t].push({ name: d.name, minutes: d.early_minutes || 0 })
      }
    })
    Object.keys(latePeopleMap).forEach(k => latePeopleMap[k].sort((a, b) => b.minutes - a.minutes))
    Object.keys(earlyPeopleMap).forEach(k => earlyPeopleMap[k].sort((a, b) => b.minutes - a.minutes))
    return { teamMap, latePeopleMap, earlyPeopleMap }
  }

  function formatTooltip(params, maps) {
    const team = params[0].name
    const lateList = maps.latePeopleMap[team] || []
    const earlyList = maps.earlyPeopleMap[team] || []
    const lateLabel = '晚签'
    const earlyLabel = '早退'
    let html = `${team} - ${lateLabel}: ${lateList.length}人 / ${earlyLabel}: ${earlyList.length}人\n`
    if (!lateList.length && !earlyList.length) {
      html += '无晚签/早退记录'
      return html
    }
    if (lateList.length) {
      html += `${lateLabel}明细:\n`
      lateList.slice(0, 8).forEach(p => {
        html += `${p.name} ${lateLabel} ${p.minutes}分\n`
      })
      if (lateList.length > 8) html += `... 等 ${lateList.length} 人\n`
    }
    if (earlyList.length) {
      html += `${earlyLabel}明细:\n`
      earlyList.slice(0, 8).forEach(p => {
        html += `${p.name} ${earlyLabel} ${p.minutes}分\n`
      })
      if (earlyList.length > 8) html += `... 等 ${earlyList.length} 人\n`
    }
    return html
  }

  it('tooltip 同时显示晚签与早退两列及人数', () => {
    const maps = buildLateEarlyMaps(mergedData)
    const html = formatTooltip([{ name: '班组A' }], maps)
    expect(html).toContain('班组A - 晚签: 2人 / 早退: 1人')
    expect(html).toContain('晚签明细:')
    expect(html).toContain('早退明细:')
  })

  it('晚签列按累计分钟降序显示人名', () => {
    const maps = buildLateEarlyMaps(mergedData)
    const html = formatTooltip([{ name: '班组A' }], maps)
    expect(html).toContain('李四 晚签 45分')
    expect(html).toContain('张三 晚签 20分')
    expect(html.indexOf('李四 晚签')).toBeLessThan(html.indexOf('张三 晚签'))
  })

  it('早退列显示早退人员与累计分钟', () => {
    const maps = buildLateEarlyMaps(mergedData)
    const html = formatTooltip([{ name: '班组A' }], maps)
    expect(html).toContain('李四 早退 10分')
  })

  it('仅早退无晚签的班组：早退列正常、无晚签明细行', () => {
    const maps = buildLateEarlyMaps(mergedData)
    const html = formatTooltip([{ name: '班组B' }], maps)
    expect(html).toContain('班组B - 晚签: 0人 / 早退: 1人')
    expect(html).toContain('王五 早退 35分')
    expect(html).not.toContain('晚签明细:')
  })

  it('无晚签/早退记录的班组显示提示', () => {
    const maps = buildLateEarlyMaps([
      { emp_no: 'E001', name: '张三', team: '班组A', late_days: 0, late_minutes: 0, early_days: 0, early_minutes: 0 }
    ])
    const html = formatTooltip([{ name: '班组A' }], maps)
    expect(html).toContain('班组A - 晚签: 0人 / 早退: 0人')
    expect(html).toContain('无晚签/早退记录')
  })
})

describe('CheckinReport - 签入次数区间 tooltip 显示 top5 员工', () => {
  const data = [
    { name: 'A', checkin_count: 3, total_hours: 30 },
    { name: 'B', checkin_count: 3, total_hours: 25 },
    { name: 'C', checkin_count: 3, total_hours: 20 },
    { name: 'D', checkin_count: 3, total_hours: 15 },
    { name: 'E', checkin_count: 3, total_hours: 10 },
    { name: 'F', checkin_count: 3, total_hours: 5 },
    { name: 'G', checkin_count: 8, total_hours: 50 }
  ]

  function buildBucketTooltip(bucket, allData) {
    const people = allData
      .filter(d => d.checkin_count >= bucket.min && d.checkin_count <= bucket.max)
      .sort((a, b) => b.total_hours - a.total_hours)
      .slice(0, 5)
    let html = `${bucket.name}: ${bucket.value} 人\n`
    people.forEach(p => {
      html += `${p.name}: ${p.checkin_count}次 / ${p.total_hours.toFixed(1)}h\n`
    })
    const totalInBucket = allData.filter(d => d.checkin_count >= bucket.min && d.checkin_count <= bucket.max).length
    if (totalInBucket > people.length) html += `... 等 ${totalInBucket} 人\n`
    return html
  }

  it('区间 tooltip 显示工时最高的前 5 名员工', () => {
    const bucket = { name: '0~5次', min: 0, max: 5, value: 6 }
    const html = buildBucketTooltip(bucket, data)
    expect(html).toContain('A: 3次 / 30.0h')
    expect(html).toContain('E: 3次 / 10.0h')
    // 人数超过 5 时提示剩余人数
    expect(html).toContain('... 等 6 人')
  })

  it('区间 tooltip 前 5 名按工时降序', () => {
    const bucket = { name: '0~5次', min: 0, max: 5, value: 6 }
    const html = buildBucketTooltip(bucket, data)
    const names = ['A', 'B', 'C', 'D', 'E']
    const positions = names.map(n => html.indexOf(n))
    for (let i = 1; i < positions.length; i++) {
      expect(positions[i]).toBeGreaterThan(positions[i - 1])
    }
  })
})