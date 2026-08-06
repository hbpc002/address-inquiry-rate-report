import { ref, computed, watch } from 'vue'

export function toComparableNumber(value) {
  if (value === null || value === undefined) return null
  const num = typeof value === 'number' ? value : parseFloat(value)
  return isNaN(num) ? null : num
}

const OPERATOR_FNS = {
  gt: (a, b) => a > b,
  ge: (a, b) => a >= b,
  lt: (a, b) => a < b,
  le: (a, b) => a <= b
}

export function matchesFieldConditions(row, conditions, fields) {
  for (const cond of conditions) {
    if (!cond.fieldKey || cond.value === null || cond.value === undefined || cond.value === '') continue
    const field = (fields || []).find(f => f.key === cond.fieldKey)
    if (!field) continue
    const raw = toComparableNumber(field.get ? field.get(row) : row[cond.fieldKey])
    if (raw === null) return false
    const fn = OPERATOR_FNS[cond.operator] || OPERATOR_FNS.gt
    if (!fn(raw, Number(cond.value))) return false
  }
  return true
}

export function applyFieldFilter(data, conditions, fields) {
  if (!data) return data
  if (!conditions || conditions.length === 0) return data
  return data.filter(row => matchesFieldConditions(row, conditions, fields))
}

export function useFieldFilter(fields, options = {}) {
  const fieldDefs = ref(fields || [])
  const conditions = ref([])
  const persistKey = options.persistKey || ''
  const activeCount = computed(() =>
    conditions.value.filter(c => c.fieldKey && c.value !== null && c.value !== undefined && c.value !== '').length
  )

  function addCondition() {
    const firstField = fieldDefs.value[0]
    conditions.value.push({
      fieldKey: firstField ? firstField.key : '',
      operator: 'gt',
      value: null,
      unit: firstField ? firstField.unit : 'number'
    })
  }

  function removeCondition(index) {
    conditions.value.splice(index, 1)
  }

  function clear() {
    conditions.value = []
    if (persistKey) {
      try { sessionStorage.removeItem(persistKey) } catch { /* ignore */ }
    }
  }

  function filtered(data) {
    return applyFieldFilter(data, conditions.value, fieldDefs.value)
  }

  if (persistKey) {
    try {
      const saved = sessionStorage.getItem(persistKey)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed)) conditions.value = parsed
      }
    } catch { /* ignore */ }
    watch(conditions, (val) => {
      sessionStorage.setItem(persistKey, JSON.stringify(val))
    }, { deep: true })
  }

  return {
    fields: fieldDefs,
    conditions,
    activeCount,
    addCondition,
    removeCondition,
    clear,
    filtered
  }
}
