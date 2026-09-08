/**
 * AI 模块 store（RAG 升级新增）
 * - 推荐列表状态：recommendList / 分页 / 策略
 * - 问答历史状态：chatHistory / 分页
 * 问答消息会话状态由 AIChat.vue 本地维护（keep-alive 可保留）
 */
import { defineStore } from 'pinia'
import * as aiApi from '../../api/ai'

export const useAiStore = defineStore('ai', {
  state: () => ({
    // 个性化推荐
    recommendList: [],
    recommendTotal: 0,
    recommendHasMore: false,
    recommendStrategy: '',        // vector=向量个性化 / hot_fallback=热门兜底
    recommendLoading: false,
    recommendRefreshing: false,
    recommendFinished: false,
    recommendError: '',           // 接口不可用/失败时记录，供页面降级

    // 问答历史
    chatHistory: [],
    chatHistoryTotal: 0,
    chatHistoryHasMore: false,
    chatHistoryLoading: false,
    chatHistoryFinished: false,
  }),

  actions: {
    // 获取 AI 个性化推荐（isRefresh=true 时重置列表）
    async getRecommendList(isRefresh = false) {
      if (isRefresh) {
        this.recommendRefreshing = true
        this.recommendList = []
        this.recommendFinished = false
        this.recommendError = ''
      }
      if (this.recommendLoading) return { success: true, skipped: true }
      this.recommendLoading = true

      try {
        const page = isRefresh ? 1 : Math.ceil(this.recommendList.length / 10) + 1
        const data = await aiApi.getRecommendList({ page, pageSize: 10 })
        const list = data?.list || []
        this.recommendList = isRefresh ? list : [...this.recommendList, ...list]
        this.recommendTotal = data?.total || 0
        this.recommendHasMore = !!data?.hasMore
        this.recommendStrategy = data?.strategy || ''
        if (!data?.hasMore) {
          this.recommendFinished = true
        }
        return { success: true, data }
      } catch (error) {
        // 记录错误但不抛出，由页面决定降级策略
        this.recommendError = error?.message || '推荐服务暂不可用'
        this.recommendFinished = true
        return { success: false, message: this.recommendError, code: error?.code }
      } finally {
        this.recommendLoading = false
        this.recommendRefreshing = false
      }
    },

    // 重置推荐状态（退出登录等场景）
    resetRecommend() {
      this.recommendList = []
      this.recommendTotal = 0
      this.recommendHasMore = false
      this.recommendStrategy = ''
      this.recommendFinished = false
      this.recommendError = ''
    },

    // 获取问答历史（isRefresh=true 时重置）
    async getChatHistory(isRefresh = false) {
      if (isRefresh) {
        this.chatHistory = []
        this.chatHistoryFinished = false
      }
      if (this.chatHistoryLoading) return { success: true, skipped: true }
      this.chatHistoryLoading = true

      try {
        const page = isRefresh ? 1 : Math.ceil(this.chatHistory.length / 10) + 1
        const data = await aiApi.getChatHistory({ page, pageSize: 10 })
        const list = data?.list || []
        this.chatHistory = isRefresh ? list : [...this.chatHistory, ...list]
        this.chatHistoryTotal = data?.total || 0
        this.chatHistoryHasMore = !!data?.hasMore
        if (!data?.hasMore) {
          this.chatHistoryFinished = true
        }
        return { success: true, data }
      } catch (error) {
        this.chatHistoryFinished = true
        return { success: false, message: error?.message || '获取问答历史失败', code: error?.code }
      } finally {
        this.chatHistoryLoading = false
      }
    },
  },
})
