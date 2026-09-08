<template>
  <div class="ai-history-page">
    <van-nav-bar
      :title="$t('aiHistory.title')"
      left-arrow
      @click-left="$router.back()"
      fixed
    />
    
    <div class="history-content">
      <!-- 未登录：引导登录 -->
      <van-empty v-if="!isLogin" :description="$t('aiHistory.loginPrompt')">
        <van-button type="primary" size="small" @click="goLogin">{{ $t('common.login') }}</van-button>
      </van-empty>

      <template v-else>
        <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
          <van-list
            v-model:loading="aiStore.chatHistoryLoading"
            :finished="aiStore.chatHistoryFinished"
            :finished-text="$t('home.noMore')"
            @load="onLoad"
          >
            <van-empty v-if="!aiStore.chatHistory.length && !aiStore.chatHistoryLoading" :description="$t('aiHistory.empty')" />

            <div
              v-for="item in aiStore.chatHistory"
              :key="item.id"
              class="history-item"
            >
              <div class="history-question">
                <span class="q-icon">Q</span>
                <span class="q-text">{{ item.question }}</span>
              </div>
              <div class="history-answer">{{ item.answer }}</div>
              <div class="history-footer">
                <span class="history-time">{{ item.createdAt }}</span>
                <source-card v-if="item.sources && item.sources.length" :sources="item.sources" class="history-sources" />
              </div>
            </div>
          </van-list>
        </van-pull-refresh>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAiStore } from '../store/modules/ai'
import { useUserStore } from '../store/user'
import SourceCard from '../components/SourceCard.vue'

const router = useRouter()
const aiStore = useAiStore()
const userStore = useUserStore()
const isLogin = computed(() => userStore.getLoginStatus)
const refreshing = ref(false)

onMounted(() => {
  if (isLogin.value) {
    aiStore.getChatHistory(true)
  } else {
    aiStore.chatHistoryFinished = true
  }
})

const onLoad = () => {
  aiStore.getChatHistory()
}

const onRefresh = async () => {
  refreshing.value = true
  await aiStore.getChatHistory(true)
  refreshing.value = false
}

const goLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.ai-history-page {
  min-height: 100vh;
  background-color: #f7f8fa;
}

.history-content {
  padding-top: 46px;
  padding-bottom: 20px;
}

.history-item {
  background-color: #fff;
  margin: 10px 12px;
  border-radius: 8px;
  padding: 12px 14px;
}

.history-question {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.q-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background-color: #1989fa;
  color: #fff;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.q-text {
  flex: 1;
  line-height: 1.5;
}

.history-answer {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  margin-bottom: 8px;
}

.history-footer {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-time {
  font-size: 12px;
  color: #999;
}

.history-sources {
  margin-top: 0;
}
</style>
