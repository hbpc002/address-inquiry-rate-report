import { reactive, onBeforeUnmount } from 'vue'

export function usePersistedFilters(storageKey, defaults) {
  let initial = { ...defaults }
  let isRestored = false
  try {
    const saved = sessionStorage.getItem(storageKey)
    if (saved) {
      const parsed = JSON.parse(saved)
      isRestored = true
      initial = { ...defaults, ...parsed }
    }
  } catch {
    sessionStorage.removeItem(storageKey)
  }
  const filters = reactive(initial)

  function save() {
    sessionStorage.setItem(storageKey, JSON.stringify(filters))
  }

  onBeforeUnmount(save)

  function resetFilters() {
    Object.assign(filters, { ...defaults })
    sessionStorage.removeItem(storageKey)
  }

  return { filters, resetFilters, isRestored }
}