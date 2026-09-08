import { defineStore } from 'pinia'
import * as newsApi from '../../api/news'

export const useNewsStore = defineStore('news', {
  state: () => ({
    newsList: [],
    newsDetail: {},
    categories: [],
    currentCategory: 1,
    loading: false,
    refreshing: false,
    finished: false,
    categoriesLoading: false
  }),
  
  actions: {
    // 获取新闻分类
    async getCategories() {
      if (this.categoriesLoading) return;

      this.categoriesLoading = true;

      try {
        const data = await newsApi.getCategories();

        if (Array.isArray(data)) {
          this.categories = [...data, { id: 10, name: '更多' }];

          if (!this.currentCategory && this.categories.length > 0) {
            this.currentCategory = this.categories[0].id;
          }
        }
      } catch (error) {
        console.error('获取新闻分类失败:', error);
        // 设置默认分类，以防API请求失败
        this.categories = [
          { id: 1, name: '头条' },
          { id: 2, name: '社会' },
          { id: 3, name: '国内' },
          { id: 4, name: '国际' },
          { id: 5, name: '娱乐' },
          { id: 6, name: '体育' },
          { id: 7, name: '科技' }
        ];
      } finally {
        this.categoriesLoading = false;
      }
    },
    
    // 切换新闻分类（与升级前行为一致：仅分类变化时重置并刷新）
    changeCategory(categoryId) {
      if (this.currentCategory !== categoryId) {
        this.currentCategory = categoryId
        this.newsList = []
        this.finished = false
        this.getNewsList(true)
      }
    },
    
    // 获取新闻列表
    async getNewsList(isRefresh = false) {
      if (isRefresh) {
        this.refreshing = true
        this.newsList = []
        this.finished = false
      }

      this.loading = true

      try {
        const params = {
          categoryId: this.currentCategory,
          page: isRefresh ? 1 : Math.ceil(this.newsList.length / 10) + 1,
          pageSize: 10
        }

        const data = await newsApi.getNewsList(params)
        const newsData = data?.list || []

        this.newsList = isRefresh ? newsData : [...this.newsList, ...newsData]

        if (newsData.length < params.pageSize || !data?.hasMore) {
          this.finished = true;
        }
      } catch (error) {
        console.error('获取新闻列表失败:', error)
      } finally {
        this.loading = false
        this.refreshing = false
      }
    },
    
    // 获取新闻详情
    async getNewsDetail(id) {
      try {
        const data = await newsApi.getNewsDetail(id)

        if (data && data.id) {
          this.newsDetail = data;
          return;
        }
        console.error('获取新闻详情失败: 接口返回错误');
      } catch (error) {
        console.error('获取新闻详情失败:', error);
      }
    },
    
    // 获取分类名称
    getCategoryName(categoryId) {
      const category = this.categories.find(item => item.id === categoryId)
      return category ? category.name : '未知'
    }
  }
})
