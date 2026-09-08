/**
 * 统一请求封装 request.js
 * - axios 实例：baseURL、超时
 * - 请求拦截器：统一注入 Authorization token
 * - 响应拦截器：统一解包 { code, message, data }；401 清登录态并跳登录
 * - 导出 ApiError 供业务层识别错误码（503 等用于 AI 降级）
 */
import axios from 'axios'
import { apiConfig } from '../config/api'

// 业务错误类：携带业务 code，供调用方按 code 降级
export class ApiError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

// 从 localStorage 读取持久化的用户 token（key 与 store/user.js persist 配置一致）
export function getToken() {
  try {
    const raw = localStorage.getItem('user-store')
    if (raw) {
      const parsed = JSON.parse(raw)
      return parsed?.token || ''
    }
  } catch (e) {
    /* ignore */
  }
  return ''
}

// 清除登录态并跳转登录页
export function handleUnauthorized() {
  try {
    localStorage.removeItem('user-store')
  } catch (e) {
    /* ignore */
  }
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

const service = axios.create({
  baseURL: apiConfig.baseURL,
  timeout: 30000,
})

// 请求拦截器：统一注入 token
service.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = token
  }
  return config
})

// 响应拦截器：统一解包
service.interceptors.response.use(
  (res) => {
    const body = res.data
    // 兼容非标准响应（直接返回业务数据）
    if (!body || typeof body !== 'object') {
      return body
    }
    if (body.code === 200) {
      return body.data
    }
    if (body.code === 401) {
      handleUnauthorized()
    }
    return Promise.reject(new ApiError(body.code ?? res.status, body.message || '请求失败'))
  },
  (err) => {
    const status = err.response?.status
    const body = err.response?.data
    // 登录接口的 401 表示"用户名或密码错误"，不应触发登出清理
    if (status === 401 && !err.config?.url?.includes('/login')) {
      handleUnauthorized()
    }
    const code = body?.code ?? status ?? 0
    // FastAPI 错误体为 { detail: "..." }，此处兜底读取
    const message = body?.message || body?.detail || err.message || '网络请求失败'
    return Promise.reject(new ApiError(code, message))
  }
)

export default service
