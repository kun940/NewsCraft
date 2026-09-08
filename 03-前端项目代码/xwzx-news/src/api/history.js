/**
 * 浏览历史模块 API
 * 对应旧接口 /api/history/*（需认证，token 由 request 拦截器统一注入）
 */
import request from './request'

// 添加浏览记录
export function addHistory(newsId) {
  return request.post('/api/history/add', { newsId })
}

// 获取浏览历史列表（分页）
export function getHistoryList({ page = 1, pageSize = 10 } = {}) {
  return request.get('/api/history/list', { params: { page, pageSize } })
}

// 删除单条浏览记录
export function deleteHistory(historyId) {
  return request.delete(`/api/history/delete/${historyId}`)
}

// 清空浏览历史
export function clearHistory() {
  return request.delete('/api/history/clear')
}
