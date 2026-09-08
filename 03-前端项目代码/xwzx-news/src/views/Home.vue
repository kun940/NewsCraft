<template>
  <div class="home">
    <van-nav-bar :title="$t('home.title')" fixed />
    
    <!-- 更多选项独立div -->
    <div class="more-options">
      <div class="more-tab" @click="goToCategory">
        {{ $t('home.more') }} <van-icon name="arrow" />
      </div>
    </div>
    
    <!-- 精选 / AI推荐 双模式切换 -->
    <mode-switch :model-value="mode" class="home-mode-switch" @update:model-value="onModeChange" />

    <!-- 精选模式：分类Tab + 传统新闻列表（旧接口，保持原行为） -->
    <div v-if="mode === 'classic'" class="category-tabs">
      <van-tabs v-model:active="activeTab" sticky swipeable animated>
        <van-tab 
          v-for="(category, index) in displayCategories" 
          :key="category.id" 
          :title="getCategoryTranslation(category.name)"
          @click="changeCategory(category.id)"
        >
          <van-pull-refresh v-model="newsStore.refreshing" @refresh="onRefresh">
            <van-list
              v-model:loading="newsStore.loading"
              :finished="newsStore.finished"
              :finished-text="$t('home.noMore')"
              @load="onLoad"
            >
              <news-item 
                v-for="item in newsStore.newsList" 
                :key="item.id" 
                :news="item" 
              />
            </van-list>
          </van-pull-refresh>
        </van-tab>
      </van-tabs>
    </div>
    
    <!-- AI推荐模式：个性化推荐列表（新接口，未登录/失败时降级） -->
    <div v-else class="ai-recommend">
      <van-pull-refresh v-model="aiStore.recommendRefreshing" @refresh="onAiRefresh">
        <van-list
          v-model:loading="aiStore.recommendLoading"
          :finished="aiStore.recommendFinished"
          :finished-text="$t('home.noMore')"
          @load="onAiLoad"
        >
          <!-- 未登录：引导登录 -->
          <van-empty v-if="!isLogin" :description="$t('home.aiLoginPrompt')">
            <van-button type="primary" size="small" @click="goLogin">{{ $t('common.login') }}</van-button>
          </van-empty>

          <!-- 已登录但接口异常：空态 -->
          <van-empty v-else-if="aiStore.recommendError && !aiStore.recommendList.length" :description="aiStore.recommendError" />

          <!-- 推荐列表 -->
          <template v-else>
            <div v-if="aiStore.recommendStrategy" class="ai-strategy-tip">
              <van-icon name="fire-o" />
              {{ aiStore.recommendStrategy === 'vector' ? $t('home.aiStrategyVector') : $t('home.aiStrategyHot') }}
            </div>
            <div
              v-for="item in aiStore.recommendList"
              :key="item.id"
              class="ai-news-item"
            >
              <news-item :news="item" />
              <div class="ai-news-meta">
                <div v-if="item.reason" class="ai-reason">
                  <van-icon name="bulb-o" /> {{ item.reason }}
                </div>
                <ai-tags v-if="item.aiTags" :tags="item.aiTags" />
              </div>
            </div>
          </template>
        </van-list>
      </van-pull-refresh>
    </div>
    
    <tab-bar />
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, onBeforeUnmount } from 'vue'
import { useNewsStore } from '../store/modules/news'
import { useAiStore } from '../store/modules/ai'
import { useUserStore } from '../store/user'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { showToast } from 'vant'
import NewsItem from '../components/NewsItem.vue'
import TabBar from '../components/TabBar.vue'
import ModeSwitch from '../components/ModeSwitch.vue'
import AITags from '../components/AITags.vue'

// 显式组件名：keep-alive 按 name 缓存本页（返回详情时保留 tab 与滚动状态）
defineOptions({ name: 'Home' })

const newsStore = useNewsStore()
const aiStore = useAiStore()
const userStore = useUserStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const activeTab = ref(0)
const tabsTop = ref(0)
const mode = ref('classic') // classic=精选 / ai=AI推荐
const isLogin = computed(() => userStore.getLoginStatus)

// 监听路由参数 mode（支持 /home?mode=ai 直达 AI 推荐）
watch(
  () => route.query.mode,
  (m) => {
    if (m === 'ai') {
      mode.value = 'ai'
      ensureAiList()
    } else if (m === 'classic') {
      mode.value = 'classic'
    }
  },
  { immediate: true }
)

// 监听路由变化（分类直达）
watch(
  () => route.query.categoryId,
  (newCategoryId) => {
    if (newCategoryId) {
      const categoryId = parseInt(newCategoryId)
      const filteredCategories = newsStore.categories.filter(category => category.name !== '更多')
      const index = filteredCategories.findIndex(cat => cat.id === categoryId)
      
      if (index !== -1) {
        activeTab.value = index
        newsStore.changeCategory(categoryId)
      }
    }
  },
  { immediate: true }
)

onMounted(() => {
  newsStore.getCategories().then(() => {
    newsStore.getNewsList()
  })
  
  setTimeout(updateTabsPosition, 300)
  window.addEventListener('scroll', handleScroll)
})

// 计算属性：显示的分类（只显示非"更多"分类）
const displayCategories = computed(() => {
  return newsStore.categories.filter(category => category.name !== '更多');
})

// 获取分类名称的翻译
const getCategoryTranslation = (categoryName) => {
  const categoryMap = {
    '头条': 'headline',
    '社会': 'society',
    '国内': 'domestic',
    '国际': 'international',
    '娱乐': 'entertainment',
    '体育': 'sports',
    '军事': 'military',
    '科技': 'technology',
    '财经': 'finance',
    '更多': 'more'
  };
  
  const key = categoryMap[categoryName];
  return key ? t(`home.categories.${key}`) : categoryName;
}

// 跳转到分类页面
const goToCategory = () => {
  router.push('/category')
}

// 去登录
const goLogin = () => {
  router.push('/login')
}

// 模式切换
const onModeChange = (m) => {
  mode.value = m
  if (m === 'ai') {
    ensureAiList()
  }
  router.replace({ query: m === 'ai' ? { mode: 'ai' } : {} })
}

// 确保 AI 推荐列表已加载（未登录时不发请求，避免 401 跳转）
async function ensureAiList() {
  if (!isLogin.value) {
    aiStore.recommendFinished = true
    return
  }
  if (!aiStore.recommendList.length) {
    const result = await aiStore.getRecommendList(true)
    if ((!result || !result.success) && result?.code !== 401) {
      showToast(t('home.recommendFailed'))
      mode.value = 'classic'
      router.replace({ query: {} })
      aiStore.resetRecommend()
    }
  }
}

// AI 推荐：上拉加载更多
const onAiLoad = async () => {
  if (!isLogin.value) {
    aiStore.recommendFinished = true
    return
  }
  const result = await aiStore.getRecommendList()
  if ((!result || !result.success) && result?.code !== 401) {
    // AI 接口不可用：提示并自动回退精选模式
    showToast(t('home.recommendFailed'))
    mode.value = 'classic'
    router.replace({ query: {} })
    aiStore.resetRecommend()
  }
}

// AI 推荐：下拉刷新
const onAiRefresh = async () => {
  if (!isLogin.value) {
    aiStore.recommendFinished = true
    return
  }
  const result = await aiStore.getRecommendList(true)
  if ((!result || !result.success) && result?.code !== 401) {
    showToast(t('home.recommendFailed'))
    mode.value = 'classic'
    router.replace({ query: {} })
    aiStore.resetRecommend()
  }
}

// 获取分类导航栏的位置并设置滚动监听
const updateTabsPosition = () => {
  const tabsElement = document.querySelector('.van-tabs__wrap')
  if (tabsElement) {
    tabsTop.value = tabsElement.getBoundingClientRect().top
  }
}

// 滚动事件处理
const handleScroll = () => {
  updateTabsPosition()
}

onMounted(() => {
  newsStore.getNewsList()
  setTimeout(updateTabsPosition, 300)
  window.addEventListener('scroll', handleScroll)
})

// 组件销毁前移除事件监听
onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
})

// 监听分类变化
watch(activeTab, (newVal) => {
  const categoryId = newsStore.categories[newVal]?.id
  if (categoryId) {
    newsStore.changeCategory(categoryId)
  }
})

// 下拉刷新（精选）
const onRefresh = () => {
  newsStore.getNewsList(true)
}

// 上拉加载更多（精选）
const onLoad = () => {
  newsStore.getNewsList()
}

// 切换分类（精选）
const changeCategory = (categoryId) => {
  if (categoryId === 10) {
    goToCategory()
    return
  }
  newsStore.changeCategory(categoryId)
}
</script>

<style scoped>
.home {
  padding-top: 46px;
  padding-bottom: 50px;
  background-color: #f7f8fa;
  min-height: 100vh;
}

.home-mode-switch {
  margin: 6px 0 0;
}

.category-tabs {
  margin-bottom: 10px;
  position: relative;
}

:deep(.van-tabs__wrap) {
  background-color: #fff;
}

:deep(.van-tab) {
  font-size: 14px;
}

:deep(.van-tab--active) {
  font-weight: bold;
  color: #1989fa;
}

.more-options {
  position: fixed;
  right: 0;
  background-color: #fff;
  padding: 0;
  border-radius: 4px 0 0 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  top: v-bind('tabsTop + "px"');
  height: 44px;
  display: flex;
  align-items: center;
}

.more-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #1989fa;
  font-weight: bold;
  height: 100%;
  padding: 0 10px;
}

/* AI 推荐区 */
.ai-recommend {
  margin-top: 10px;
}

.ai-strategy-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #1989fa;
  background-color: rgba(25, 137, 250, 0.06);
  padding: 6px 12px;
}

.ai-news-item {
  background-color: #fff;
  margin-bottom: 8px;
}

.ai-news-meta {
  padding: 0 16px 10px;
  border-bottom: 1px solid #f2f2f2;
}

.ai-reason {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #ff9500;
  margin-top: 4px;
}
</style>
