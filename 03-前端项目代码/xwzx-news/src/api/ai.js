/**
 * AI 模块 API（RAG 升级新增，对应 /api/ai/*）
 * - recommend：个性化推荐（分页）
 * - chat：RAG 问答，SSE 流式（fetch 实现，不走 axios 拦截器）
 * - chatHistory：问答历史（分页）
 * 说明：全部需要认证；SSE 事件协议见《API接口规范文档-V2-RAG升级》5.4
 */
import request, { getToken, handleUnauthorized, ApiError } from './request'
import { apiConfig } from '../config/api'

// AI 个性化推荐
export function getRecommendList({ page = 1, pageSize = 10 } = {}) {
  return request.get('/api/ai/news/recommend', { params: { page, pageSize } })
}

/**
 * RAG 问答（SSE 流式）
 * @param {object} options
 * @param {string} options.question 用户问题
 * @param {(event: string, data: object) => void} options.onEvent 事件回调（start/delta/sources/done/error）
 * @param {AbortSignal} [options.signal] 取消信号
 */
export async function chatRAG({ question, onEvent, signal }) {
  const token = getToken()
  let res
  try {
    res = await fetch(`${apiConfig.baseURL}/api/ai/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: token } : {}),
      },
      body: JSON.stringify({ question, stream: true }),
      signal,
    })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new ApiError(0, '网络请求失败，请检查后端服务')
  }

  if (res.status === 401) {
    handleUnauthorized()
    throw new ApiError(401, '未登录或登录已过期')
  }
  if (res.status === 503) {
    throw new ApiError(503, 'AI 服务暂不可用，请稍后再试')
  }
  if (!res.ok) {
    // 尝试读取后端 JSON 错误
    let message = `请求失败 (${res.status})`
    try {
      const body = await res.json()
      message = body?.message || message
    } catch (e) {
      /* ignore */
    }
    throw new ApiError(res.status, message)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE 事件以空行分隔
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      parseSseEvent(part, onEvent)
    }
  }
  // 处理尾部未闭合事件
  if (buffer.trim()) {
    parseSseEvent(buffer, onEvent)
  }
}

// 解析单个 SSE 事件块：event: xxx\ndata: json
function parseSseEvent(block, onEvent) {
  const eventMatch = block.match(/^event:\s*(.+)$/m)
  const dataMatch = block.match(/^data:\s*(.+)$/m)
  const event = eventMatch ? eventMatch[1].trim() : 'message'
  const rawData = dataMatch ? dataMatch[1].trim() : ''
  if (!rawData || rawData === '[DONE]') {
    if (onEvent) onEvent(event, null)
    return
  }
  try {
    if (onEvent) onEvent(event, JSON.parse(rawData))
  } catch (e) {
    if (onEvent) onEvent(event, { content: rawData })
  }
}

// 获取问答历史（分页）
export function getChatHistory({ page = 1, pageSize = 10 } = {}) {
  return request.get('/api/ai/chat/history', { params: { page, pageSize } })
}
