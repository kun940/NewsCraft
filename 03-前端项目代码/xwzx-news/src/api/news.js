/**
 * 新闻模块 API
 * 对应旧接口 /api/news/*（列表/详情响应含可选 AI 字段，旧后端无此字段时忽略）
 */
import request from './request'

// 获取新闻分类
export function getCategories() {
  return request.get('/api/news/categories')
}

// 获取新闻列表（分类必填，支持分页）
export function getNewsList({ categoryId, page = 1, pageSize = 10 }) {
  return request.get('/api/news/list', { params: { categoryId, page, pageSize } })
}

// 获取新闻详情
export function getNewsDetail(id) {
  return request.get('/api/news/detail', { params: { id } })
}
