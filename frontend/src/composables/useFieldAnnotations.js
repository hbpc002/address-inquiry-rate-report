import { ref } from 'vue'
import { api } from '../stores/user'

const cache = ref({})

export function useFieldAnnotations(reportType) {
  const loading = ref(false)

  async function loadAnnotations() {
    if (cache.value[reportType]) return cache.value[reportType]
    loading.value = true
    try {
      const res = await api.get('/field-annotations/public', {
        params: { report_type: reportType },
      })
      const map = {}
      for (const item of res.data || []) {
        map[item.field_path] = item
      }
      cache.value[reportType] = map
      return map
    } catch {
      cache.value[reportType] = {}
      return {}
    } finally {
      loading.value = false
    }
  }

  function getAnnotation(fieldPath) {
    return cache.value[reportType]?.[fieldPath] || null
  }

  return { loadAnnotations, getAnnotation, loading }
}
