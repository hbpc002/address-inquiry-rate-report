const SCOPE_SEPARATOR = '\u0001'

export function deptShort(dept) {
  const text = String(dept || '').trim()
  if (!text) return ''
  const parts = text.split(/>>|\/|＞|>|／/).map(item => item.trim()).filter(Boolean)
  return parts[parts.length - 1] || text
}

export function teamKey(dept, team) {
  return `${dept || ''}${SCOPE_SEPARATOR}${team || ''}`
}

export function classKey(dept, className) {
  return `${dept || ''}${SCOPE_SEPARATOR}${className || ''}`
}

function decorateScopedItems(items, nameKey, keyField, labelField, buildKey) {
  const rows = Array.isArray(items) ? items : []
  const counts = new Map()
  for (const item of rows) {
    if (item?.is_subtotal) continue
    const name = item?.[nameKey] || ''
    if (!name) continue
    counts.set(name, (counts.get(name) || 0) + 1)
  }
  return rows.map(item => {
    const name = item?.[nameKey] || ''
    const dept = item?.dept || ''
    const deptGroup = item?.dept_group || deptShort(dept)
    const duplicate = Boolean(name && dept && counts.get(name) > 1)
    return {
      ...item,
      [keyField]: buildKey(dept, name),
      [labelField]: duplicate ? `${name}（${deptGroup}）` : name
    }
  })
}

export function decorateTeamRows(rows = []) {
  return decorateScopedItems(rows, 'team', 'team_key', 'team_label', teamKey)
}

export function decorateTeamOptions(options = []) {
  return decorateTeamRows(options)
}

export function decorateClassOptions(options = []) {
  return decorateScopedItems(options, 'class_name', 'class_key', 'class_label', classKey)
}

export function findTeamOption(options = [], key) {
  return (Array.isArray(options) ? options : []).find(item => item.team_key === key) || null
}

export function findClassOption(options = [], key) {
  return (Array.isArray(options) ? options : []).find(item => item.class_key === key) || null
}
