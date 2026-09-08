<template>
  <div v-if="list.length" class="source-card">
    <div class="source-title">
      <van-icon name="link-o" />
      <span>{{ $t('aiChat.sources') }}</span>
    </div>
    <div
      v-for="source in list"
      :key="source.newsId"
      class="source-item"
      @click="goDetail(source.newsId)"
    >
      <span class="source-index">{{ indexOf(source) + 1 }}</span>
      <span class="source-title-text">{{ source.title || `新闻 #${source.newsId}` }}</span>
      <van-icon name="arrow" class="source-arrow" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  // 引用溯源：[{ newsId, title }]
  sources: {
    type: Array,
    default: () => []
  }
})

const router = useRouter()

const list = computed(() => (props.sources || []).filter((s) => s && s.newsId))

const indexOf = (source) => list.value.findIndex((s) => s.newsId === source.newsId)

const goDetail = (newsId) => {
  if (newsId) {
    router.push(`/news/detail/${newsId}`)
  }
}
</script>

<style scoped>
.source-card {
  margin-top: 8px;
  background-color: #f8f9fb;
  border: 0.5px solid #e8eaf0;
  border-radius: 8px;
  padding: 8px 10px;
}

.source-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 6px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  font-size: 13px;
  color: #1989fa;
  cursor: pointer;
}

.source-index {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background-color: #1989fa;
  color: #fff;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.source-title-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-arrow {
  flex-shrink: 0;
  font-size: 12px;
  color: #c8c9cc;
}
</style>
