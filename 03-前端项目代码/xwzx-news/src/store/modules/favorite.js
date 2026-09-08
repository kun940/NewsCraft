import { defineStore } from 'pinia';
import { useUserStore } from '../user';
import * as favoriteApi from '../../api/favorite';

export const useFavoriteStore = defineStore('favorite', {
  state: () => ({
    favorites: [],
    loading: false,
  }),
  
  getters: {
    getFavorites: (state) => state.favorites,
    isFavorite: (state) => (id) => state.favorites.some(item => item.id === id),
  },
  
  actions: {
    // 检查文章收藏状态 - API请求
    async checkFavoriteStatusApi(newsId) {
      const userStore = useUserStore();
      // 检查用户是否登录
      if (!userStore.getLoginStatus) {
        return {
          success: true,
          isFavorite: this.isFavorite(newsId),
          isLocal: true
        };
      }

      try {
        this.loading = true;
        const data = await favoriteApi.checkFavorite(newsId);

        return {
          success: true,
          isFavorite: data?.isFavorite ?? false
        };
      } catch (error) {
        console.error('检查收藏状态请求失败:', error);
        // 如果API请求失败，回退到本地状态检查
        return {
          success: true,
          isFavorite: this.isFavorite(newsId),
          isLocal: true
        };
      } finally {
        this.loading = false;
      }
    },
    
    // 添加收藏 - API请求
    async addFavoriteApi(newsId) {
      const userStore = useUserStore();

      if (!userStore.getLoginStatus) {
        return { success: false, message: '请先登录' };
      }

      try {
        this.loading = true;
        const data = await favoriteApi.addFavorite(newsId);
        return { success: true, data };
      } catch (error) {
        console.error('添加收藏请求失败:', error);
        return { success: false, message: error?.message || '网络请求失败' };
      } finally {
        this.loading = false;
      }
    },
    
    // 取消收藏 - API请求
    async removeFavoriteApi(newsId) {
      const userStore = useUserStore();

      if (!userStore.getLoginStatus) {
        return { success: false, message: '请先登录' };
      }

      try {
        this.loading = true;
        await favoriteApi.removeFavorite(newsId);
        return { success: true };
      } catch (error) {
        console.error('取消收藏请求失败:', error);
        return { success: false, message: error?.message || '网络请求失败' };
      } finally {
        this.loading = false;
      }
    },
    
    // 添加收藏 - 本地
    addFavorite(news) {
      if (!this.isFavorite(news.id)) {
        this.favorites.unshift({
          ...news,
          favoriteTime: new Date().toLocaleString()
        });
        this.saveFavorites();
      }
    },
    
    // 取消收藏 - 本地
    removeFavorite(id) {
      this.favorites = this.favorites.filter(item => item.id !== id);
      this.saveFavorites();
    },
    
    // 切换收藏状态 - 结合API和本地
    async toggleFavorite(news) {
      if (!news || !news.id) {
        console.error('无效的新闻对象:', news);
        return null;
      }

      if (this.isFavorite(news.id)) {
        const result = await this.removeFavoriteApi(news.id);
        if (result.success) {
          this.removeFavorite(news.id);
          return false;
        }
        return null;
      } else {
        const result = await this.addFavoriteApi(news.id);
        if (result.success) {
          this.addFavorite(news);
          return true;
        }
        return null;
      }
    },
    
    // 清空收藏 - 本地
    clearFavorites() {
      this.favorites = [];
      this.saveFavorites();
    },
    
    // 清空收藏 - API请求
    async clearFavoritesApi() {
      const userStore = useUserStore();

      if (!userStore.getLoginStatus) {
        return { success: false, message: '请先登录' };
      }

      try {
        this.loading = true;
        await favoriteApi.clearFavorite();
        this.clearFavorites();
        return { success: true };
      } catch (error) {
        console.error('清空收藏请求失败:', error);
        return { success: false, message: error?.message || '网络请求失败' };
      } finally {
        this.loading = false;
      }
    },
    
    // 保存到本地存储
    saveFavorites() {
      localStorage.setItem('news_favorites', JSON.stringify(this.favorites));
    },
    
    // 从本地存储加载
    loadFavorites() {
      const savedFavorites = localStorage.getItem('news_favorites');
      if (savedFavorites) {
        this.favorites = JSON.parse(savedFavorites);
      }
    },
    
    // 获取收藏列表 - API请求
    async getFavoriteListApi(page = 1, pageSize = 10) {
      const userStore = useUserStore();

      if (!userStore.getLoginStatus) {
        return { success: false, message: '请先登录' };
      }

      try {
        this.loading = true;
        const data = await favoriteApi.getFavoriteList({ page, pageSize });
        this.favorites = data?.list || [];
        return { success: true, data };
      } catch (error) {
        return { success: false, message: error?.message || '网络请求失败' };
      } finally {
        this.loading = false;
      }
    },
  },
});
