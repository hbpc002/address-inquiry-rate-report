import { describe, it, expect } from 'vitest'
import { getWorkloadDetailDateRange } from '../src/utils/workloadDetailRange'

describe('getWorkloadDetailDateRange', () => {
  it('按天时显示所选日期所在月份', () => {
    const range = getWorkloadDetailDateRange({
      type: 'day', date: '2026-06-28', month: '', start_date: '', end_date: ''
    })
    expect(range).toEqual({ startDate: '2026-06-01', endDate: '2026-06-30' })
  })

  it('按月时显示查询的完整月份', () => {
    const range = getWorkloadDetailDateRange({
      type: 'month', date: '', month: '2026-02', start_date: '', end_date: ''
    })
    expect(range).toEqual({ startDate: '2026-02-01', endDate: '2026-02-28' })
  })

  it('自定义时显示自定义时间段', () => {
    const range = getWorkloadDetailDateRange({
      type: 'range', date: '', month: '', start_date: '2026-05-10', end_date: '2026-05-12'
    })
    expect(range).toEqual({ startDate: '2026-05-10', endDate: '2026-05-12' })
  })

  it('无有效选择时回退到运行时刻所在自然月', () => {
    const now = new Date()
    const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const lastDay = `${ym}-${String(new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()).padStart(2, '0')}`
    const range = getWorkloadDetailDateRange({ type: 'day', date: '', month: '', start_date: '', end_date: '' })
    expect(range).toEqual({ startDate: `${ym}-01`, endDate: lastDay })
  })
})