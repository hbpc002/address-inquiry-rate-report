import { api } from '../stores/user'
import { ElMessage } from 'element-plus'

export async function downloadBlob(url, params, defaultFilename = 'export.csv') {
  try {
    const res = await api.get(url, { params, responseType: 'blob' })
    const disposition = res.headers?.['content-disposition'] || ''
    const match = disposition.match(/filename\*?=(?:UTF-8'')?([^;\s]+)/i)
    const filename = match ? decodeURIComponent(match[1]) : defaultFilename
    const blobUrl = URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename
    link.click()
    URL.revokeObjectURL(blobUrl)
    ElMessage.success('导出成功')
  } catch (e) {
    const errData = e.response?.data
    if (errData instanceof Blob) {
      const text = await errData.text()
      try { ElMessage.error(JSON.parse(text).detail || '导出失败') } catch { ElMessage.error(text || '导出失败') }
    } else {
      ElMessage.error('导出失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}
