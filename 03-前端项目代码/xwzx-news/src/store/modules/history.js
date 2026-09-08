import { defineStore } from 'pinia';
import { useUserStore } from '../user';
import * as historyApi from '../../api/history';

export const useHistoryStore = defineStore('history', {
  state: () => ({
    history: [],
  }),
  
  getters: {
    getHistory: (state) => state.history,
  },
  
  actions: {
    // 添加浏览历史 - API请求
    async addHistoryApi(newsId) {
      const userStore = useUserStore();

      if (!userStore.getLoginStatus) {
        return { success: false, message: '请先登录' };
      }

      try {
        const data = await historyApi.addHistory(newsId);
        return { success: true, data };
      } catch (error) {
        console.error('添加浏览历史请求失败:', error);
        return { success: false, message: error?.message || '网络请求失败' };
      }
    },
    
    // 添加浏览历史 - 本地
    addHistory(news) {
      const existingIndex = this.history.findIndex(item => item.id === news.id);

      if (existingIndex !== -1) {
        this.history.splice(existingIndex, 1);
      }

      this.history.unshift({
        ...news,
        viewTime: new Date().toLocaleString()
      });

      if (this.history.length > 50) {
        this.history.pop();
      }

      this.saveHistory();
    },
    
    // 清空浏览历史 - 本地
    clearHistory() {
      this.history = [];
      this.saveHistory();
    },
    
    // 清空浏览历史 - API请求
    async clearHistoryApi() {
      const userStore = useUserStore();

      if (!userStore.getLoginStatus) {
        console.log('清空浏览历史API：用户未登录，使用本地操作');
        this.clearHistory();
        return { success: true, isLocal: true };
      }

      try {
        await historyApi.clearHistory();
        this.clearHistory();
        return { success: true };
      } catch (error) {
        console.error('清空浏览历史API：请求异常', error);
        return { success: false, message: error?.message || '网络请求失败' };
      }
    },
    
    // 删除单条浏览历史 - 本地
    removeHistory(id) {
      this.history = this.history.filter(item => item.id !== id);
      this.saveHistory();
    },
    
    // 删除单条浏览历史 - API请求
    async removeHistoryApi(id) {
      const userStore = useUserStore();

      if (!userStore.getLoginStatus) {
        console.log('删除浏览历史API：用户未登录，使用本地操作');
        this.removeHistory(id);
        return { success: true, isLocal: true };
      }

      try {
        await historyApi.deleteHistory(id);
        this.removeHistory(id);
        return { success: true };
      } catch (error) {
        console.error('删除浏览历史API：请求异常', error);
        return { success: false, message: error?.message || '网络请求失败' };
      }
    },
    
    // 保存到本地存储
    saveHistory() {
      localStorage.setItem('news_history', JSON.stringify(this.history));
    },
    
    // 从本地存储加载
    loadHistory() {
      const savedHistory = localStorage.getItem('news_history');
      if (savedHistory) {
        this.history = JSON.parse(savedHistory);
      }
    },
    
    // 获取浏览历史 - API请求
    async getHistoryListApi(page = 1, pageSize = 10) {
      const userStore = useUserStore();

      if (!userStore.getLoginStatus) {
        console.log('获取浏览历史API：用户未登录，使用本地数据');
        return { success: false, message: '请先登录', isLocal: true };
      }

      try {
        const data = await historyApi.getHistoryList({ page, pageSize });
        const historyList = data?.list || [];
        this.history = historyList;
        this.saveHistory();
        return { success: true, data: historyList };
      } catch (error) {
        return { success: false, message: error?.message || '网络请求失败' };
      }
    },
  },
});
