function lastDayOfMonth(ym) {
  const [y, m] = ym.split('-').map(Number)
  return `${ym}-${String(new Date(y, m, 0).getDate()).padStart(2, '0')}`
}

export function getWorkloadDetailDateRange(searchForm) {
  let startDate
  let endDate
  if (searchForm.type === 'day' && searchForm.date) {
    const ym = searchForm.date.slice(0, 7)
    startDate = `${ym}-01`
    endDate = lastDayOfMonth(ym)
  } else if (searchForm.type === 'month' && searchForm.month) {
    startDate = `${searchForm.month}-01`
    endDate = lastDayOfMonth(searchForm.month)
  } else if (searchForm.type === 'range' && searchForm.start_date && searchForm.end_date) {
    startDate = searchForm.start_date
    endDate = searchForm.end_date
  } else {
    const now = new Date()
    const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    startDate = `${ym}-01`
    endDate = lastDayOfMonth(ym)
  }
  return { startDate, endDate }
}