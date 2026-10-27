import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AgentTimeline from '@/components/AgentTimeline.vue'

const steps = [
  { id: 's1', kind: 'thinking', title: '正在分析问题', status: 'success', durationMs: 120 },
  {
    id: 't1',
    kind: 'tool',
    title: '区间汇总',
    subject: '2026-07-01 · 2026-07-07',
    status: 'success',
    outcome: '返回 3 行',
    durationMs: 250,
    input: { start_date: '2026-07-01' },
    output: '{"rows":[1,2,3]}',
  },
  {
    id: 't2',
    kind: 'tool',
    title: '自定义查询',
    status: 'error',
    outcome: '执行失败',
    error: 'SQL 超时',
  },
]

describe('AgentTimeline', () => {
  it('展示步骤摘要、失败数和步骤列表', () => {
    const wrapper = mount(AgentTimeline, {
      props: { steps, streaming: false, startedAt: 1000, finishedAt: 2000, defaultOpen: true },
    })
    expect(wrapper.text()).toContain('已完成 3 个步骤')
    expect(wrapper.text()).toContain('1 个失败')
    expect(wrapper.text()).toContain('区间汇总')
    expect(wrapper.text()).toContain('返回 3 行')
    expect(wrapper.findAll('.agent-step')).toHaveLength(3)
  })

  it('点击步骤展开入参与结果详情', async () => {
    const wrapper = mount(AgentTimeline, {
      props: { steps, streaming: false, defaultOpen: true },
    })
    const step = wrapper.findAll('.agent-step')[1]
    expect(step.text()).not.toContain('入参')
    await step.trigger('click')
    expect(step.text()).toContain('入参')
    expect(step.text()).toContain('2026-07-01')
    expect(step.text()).toContain('结果')
    expect(step.text()).toContain('rows')
  })

  it('流式时展示当前执行步骤，并默认展开', async () => {
    const wrapper = mount(AgentTimeline, {
      props: {
        steps: [
          { id: 's1', kind: 'thinking', title: '正在分析问题', status: 'success' },
          { id: 't1', kind: 'tool', title: '区间汇总', status: 'loading', subject: '2026-07' },
        ],
        streaming: true,
        startedAt: Date.now() - 1000,
      },
    })
    expect(wrapper.text()).toContain('正在执行 · 区间汇总')
    expect(wrapper.find('.timeline-body').exists()).toBe(true)
    expect(wrapper.find('.agent-step.is-loading').exists()).toBe(true)
  })

  it('点击标题栏可折叠步骤列表', async () => {
    const wrapper = mount(AgentTimeline, {
      props: { steps, streaming: false, defaultOpen: true },
    })
    expect(wrapper.find('.timeline-body').exists()).toBe(true)
    await wrapper.find('.timeline-head').trigger('click')
    expect(wrapper.find('.timeline-body').exists()).toBe(false)
  })
})
