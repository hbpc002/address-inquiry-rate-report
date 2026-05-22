import { reactive, onBeforeUnmount } from 'vue'

export function usePersistedFilters(storageKey, defaults) {
  const saved = sessionStorage.getItem(storageKey)
  const isRestored = !!saved
  const initial = isRestored ? { ...defaults, ...JSON.parse(saved) } : { ...defaults }
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