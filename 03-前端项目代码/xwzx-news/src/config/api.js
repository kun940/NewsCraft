/**
 * API 配置文件（升级版）
 * - baseURL 支持环境变量 VITE_API_BASE_URL 覆盖
 * - AI 功能开关 VITE_AI_ENABLED（false 时隐藏 AI 入口）
 * - 安全：不再存放任何第三方大模型 API Key（已收敛到后端 /api/ai）
 */

// API基础URL配置
export const apiConfig = {
  // 后端API基础URL，优先读环境变量，默认本地开发地址
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
}

// AI 功能开关（RAG 推荐 / 问答），由后端实现情况控制
export const aiEnabled = (import.meta.env.VITE_AI_ENABLED || 'true') !== 'false'
