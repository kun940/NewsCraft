<template>
  <div v-if="tagList.length" class="ai-tags">
    <span
      v-for="(tag, index) in tagList"
      :key="index"
      class="ai-tag"
    >{{ tag }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // 逗号分隔的标签字符串，如 "科技,热点"
  tags: {
    type: String,
    default: ''
  },
  // 最多展示数量
  max: {
    type: Number,
    default: 6
  }
})

const tagList = computed(() => {
  if (!props.tags) return []
  return props.tags
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, props.max)
})
</script>

<style scoped>
.ai-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.ai-tag {
  font-size: 11px;
  color: #1989fa;
  background-color: rgba(25, 137, 250, 0.08);
  border: 0.5px solid rgba(25, 137, 250, 0.25);
  border-radius: 4px;
  padding: 1px 6px;
  line-height: 1.5;
}
</style>
