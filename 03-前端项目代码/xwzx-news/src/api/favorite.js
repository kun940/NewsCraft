/**
 * 收藏模块 API
 * 对应旧接口 /api/favorite/*（需认证，token 由 request 拦截器统一注入）
 */
import request from './request'

// 检查收藏状态
export function checkFavorite(newsId) {
  return request.get('/api/favorite/check', { params: { newsId } })
}

// 添加收藏
export function addFavorite(newsId) {
  return request.post('/api/favorite/add', { newsId })
}

// 取消收藏
export function removeFavorite(newsId) {
  return request.delete('/api/favorite/remove', { params: { newsId } })
}

// 获取收藏列表（分页）
export function getFavoriteList({ page = 1, pageSize = 10 } = {}) {
  return request.get('/api/favorite/list', { params: { page, pageSize } })
}

// 清空收藏
export function clearFavorite() {
  return request.delete('/api/favorite/clear')
}
