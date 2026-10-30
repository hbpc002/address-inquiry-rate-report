import { describe, it, expect } from 'vitest'
import {
  classKey,
  decorateClassOptions,
  decorateTeamOptions,
  deptShort,
  findClassOption,
  findTeamOption,
  teamKey
} from '../src/utils/teamIdentity'

const DEPT_A = '广西分公司>>省中心>>客户服务营销中心>>热线运营组>>A部门'
const DEPT_B = '广西分公司>>省中心>>客户服务营销中心>>热线运营组>>B部门'

describe('班组/班级组合标识', () => {
  it('同名班组按部门拆分 key，并在标签中补充部门末级', () => {
    const rows = decorateTeamOptions([
      { dept: DEPT_A, team: '一班1组' },
      { dept: DEPT_B, team: '一班1组' },
      { dept: DEPT_A, team: '二班1组' }
    ])

    expect(rows.map(row => row.team_label)).toEqual([
      '一班1组（A部门）',
      '一班1组（B部门）',
      '二班1组'
    ])
    expect(rows.map(row => row.team_key)).toEqual([
      teamKey(DEPT_A, '一班1组'),
      teamKey(DEPT_B, '一班1组'),
      teamKey(DEPT_A, '二班1组')
    ])
    expect(findTeamOption(rows, teamKey(DEPT_B, '一班1组')).dept).toBe(DEPT_B)
  })

  it('班级选项按部门隔离，非法数据回退为空列表', () => {
    const rows = decorateClassOptions([
      { dept: DEPT_A, class_name: '一班' },
      { dept: DEPT_B, class_name: '一班' }
    ])

    expect(rows.map(row => row.class_label)).toEqual(['一班（A部门）', '一班（B部门）'])
    expect(findClassOption(rows, classKey(DEPT_A, '一班')).dept).toBe(DEPT_A)
    expect(decorateTeamOptions(null)).toEqual([])
    expect(decorateClassOptions({})).toEqual([])
    expect(findTeamOption(null, 'x')).toBeNull()
    expect(findClassOption({}, 'x')).toBeNull()
  })

  it('提取部门末级兼容多种分隔符', () => {
    expect(deptShort(DEPT_A)).toBe('A部门')
    expect(deptShort('广西>>省中心/B部门')).toBe('B部门')
    expect(deptShort('')).toBe('')
  })
})
