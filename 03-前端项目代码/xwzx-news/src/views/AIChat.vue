<template>
  <div class="ai-chat-container">
    <van-nav-bar :title="$t('aiChat.title')" fixed>
      <template #right>
        <div class="nav-right" @click="goHistory">
          <van-icon name="records" size="18" />
          <span>{{ $t('aiChat.history') }}</span>
        </div>
      </template>
    </van-nav-bar>
    
    <div class="chat-content">
      <!-- 未登录提示条 -->
      <div v-if="!isLogin" class="login-tip">
        {{ $t('aiChat.loginTip') }}
        <span class="login-tip-link" @click="goLogin">{{ $t('common.login') }}</span>
      </div>

      <div class="messages-container" ref="messagesContainer">
        <div 
          v-for="(message, index) in messages" 
          :key="index" 
          :class="['message', message.role === 'user' ? 'user-message' : 'ai-message']"
        >
          <div class="message-content">
            <div v-if="message.role === 'assistant' && message.content === ''" class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div v-else v-html="formatMessage(message.content)"></div>
            <!-- 引用溯源 -->
            <source-card v-if="message.role === 'assistant' && message.sources && message.sources.length" :sources="message.sources" />
          </div>
        </div>
      </div>
      
      <div class="input-container">
        <van-field
          v-model="userInput"
          rows="1"
          autosize
          type="textarea"
          :placeholder="$t('aiChat.placeholder')"
          class="chat-input"
          @keypress.enter.prevent="sendMessage"
        />
        <van-button 
          type="primary" 
          class="send-button" 
          :disabled="isLoading || !userInput.trim()" 
          @click="sendMessage"
        >
          {{ $t('aiChat.send') }}
        </van-button>
      </div>
    </div>
    
    <tab-bar />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, computed, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { showToast } from 'vant';

// 显式组件名：keep-alive 按 name 缓存本页
defineOptions({ name: 'AIChat' });
import * as marked from 'marked';
import DOMPurify from 'dompurify';
import TabBar from '../components/TabBar.vue';
import SourceCard from '../components/SourceCard.vue';
import { chatRAG } from '../api/ai';
import { getToken } from '../api/request';
import { useUserStore } from '../store/user';

const router = useRouter();
const { t } = useI18n();
const userStore = useUserStore();
const isLogin = computed(() => userStore.getLoginStatus);

// 聊天消息（assistant 消息可携带 sources 引用溯源）
const messages = ref([
  { role: 'assistant', content: '', sources: [] }
]);
const userInput = ref('');
const messagesContainer = ref(null);
const isLoading = ref(false);
let abortController = null;

onMounted(async () => {
  // 有 token 时刷新登录态，保证会话持久化与个性化可用
  if (getToken() && !userStore.getLoginStatus) {
    await userStore.getUserInfoDetail();
  }
  if (!messages.value[0].content) {
    messages.value[0] = {
      role: 'assistant',
      content: t('aiChat.welcome'),
      sources: []
    };
  }
  scrollToBottom();
});

onBeforeUnmount(() => {
  if (abortController) {
    abortController.abort();
  }
});

// 格式化消息内容（支持Markdown）
const formatMessage = (content) => {
  if (!content) return '';
  return DOMPurify.sanitize(marked.parse(content));
};

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return;

  // 未登录：引导登录（问答历史与个性化依赖用户身份）
  if (!isLogin.value) {
    showToast(t('aiChat.loginTip'));
    goLogin();
    return;
  }

  // 添加用户消息
  const userMessage = userInput.value.trim();
  messages.value.push({ role: 'user', content: userMessage });
  userInput.value = '';

  // 添加AI消息占位
  messages.value.push({ role: 'assistant', content: '', sources: [] });

  await nextTick();
  scrollToBottom();

  // 发送请求（后端 RAG，SSE 流式）
  isLoading.value = true;
  abortController = new AbortController();
  try {
    await chatRAG({
      question: userMessage,
      signal: abortController.signal,
      onEvent: handleChatEvent,
    });
  } catch (error) {
    console.error('AI 问答请求失败:', error);
    const last = messages.value[messages.value.length - 1];
    if (error && error.code === 401) {
      // 已由 request 层跳转登录，这里兜底提示
      last.content = t('aiChat.needLogin');
    } else if (error && error.code === 503) {
      last.content = t('aiChat.serviceUnavailable');
    } else if (error && error.name === 'AbortError') {
      last.content = t('aiChat.cancelled');
    } else {
      last.content = `${t('aiChat.error')}: ${error?.message || ''}`;
    }
    last.sources = last.sources || [];
  } finally {
    isLoading.value = false;
    abortController = null;
    await nextTick();
    scrollToBottom();
  }
};

// 处理后端 SSE 事件
const handleChatEvent = (event, data) => {
  const last = messages.value[messages.value.length - 1];
  if (!last) return;

  if (event === 'delta') {
    last.content += data?.content || '';
  } else if (event === 'sources') {
    last.sources = data?.sources || [];
  } else if (event === 'done') {
    // done 携带完整回答：仅在增量为空时使用，避免重复
    if (!last.content && data?.answer) {
      last.content = data.answer;
    }
    if (data?.sources) {
      last.sources = data.sources;
    }
  } else if (event === 'error') {
    last.content = data?.message || t('aiChat.serviceUnavailable');
  }
  scrollToBottom();
};

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// 监听消息变化，自动滚动
watch(messages, () => {
  nextTick(scrollToBottom);
}, { deep: true });

// 跳转问答历史
const goHistory = () => {
  if (!isLogin.value) {
    showToast(t('aiChat.loginTip'));
    goLogin();
    return;
  }
  router.push('/ai/history');
};

// 跳转登录
const goLogin = () => {
  router.push('/login');
};
</script>

<style scoped>
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding-top: 46px;
  padding-bottom: 50px;
  box-sizing: border-box;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  color: #1989fa;
}

.login-tip {
  background-color: #fff7e6;
  color: #d46b08;
  font-size: 12px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.login-tip-link {
  color: #1989fa;
  font-weight: 600;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.message {
  margin-bottom: 10px;
  max-width: 80%;
}

.user-message {
  margin-left: auto;
}

.ai-message {
  margin-right: auto;
}

.message-content {
  padding: 10px;
  border-radius: 10px;
  word-break: break-word;
}

.user-message .message-content {
  background-color: #007aff;
  color: white;
}

.ai-message .message-content {
  background-color: #f2f2f2;
  color: #333;
}

.input-container {
  display: flex;
  padding: 10px;
  border-top: 1px solid #eee;
  background-color: #fff;
}

.chat-input {
  flex: 1;
  margin-right: 10px;
}

.send-button {
  align-self: flex-end;
}

/* Markdown 样式 */
.message-content pre {
  background-color: #f8f8f8;
  padding: 10px;
  border-radius: 5px;
  overflow-x: auto;
}

.message-content code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
}

.message-content img {
  max-width: 100%;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  padding: 5px;
}

.typing-indicator span {
  height: 8px;
  width: 8px;
  background-color: #999;
  border-radius: 50%;
  margin: 0 2px;
  display: inline-block;
  animation: bounce 1.5s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-5px);
  }
}

:deep(pre) {
  background-color: #f0f0f0;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}

:deep(code) {
  font-family: monospace;
  background-color: #f0f0f0;
  padding: 2px 4px;
  border-radius: 4px;
}

:deep(p) {
  margin: 8px 0;
}

:deep(ul), :deep(ol) {
  padding-left: 20px;
}

:deep(a) {
  color: #1989fa;
  text-decoration: none;
}
</style>
