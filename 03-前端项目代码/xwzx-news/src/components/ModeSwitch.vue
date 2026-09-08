<template>
  <div class="mode-switch">
    <div class="mode-item" :class="{ active: modelValue === 'classic' }" @click="switchTo('classic')">
      {{ $t('home.modeClassic') }}
    </div>
    <div
      class="mode-item"
      :class="{ active: modelValue === 'ai', disabled: !aiEnabled }"
      @click="switchTo('ai')"
    >
      {{ $t('home.modeAI') }}
      <van-icon v-if="modelValue === 'ai'" name="success" class="mode-check" />
    </div>
  </div>
</template>

<script setup>
import { aiEnabled } from '../config/api'

defineProps({
  modelValue: {
    type: String,
    default: 'classic'
  }
})

const emit = defineEmits(['update:modelValue'])

const switchTo = (mode) => {
  if (mode === 'ai' && !aiEnabled) return
  emit('update:modelValue', mode)
}
</script>

<style scoped>
.mode-switch {
  position: fixed;
  top: 46px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1001;
  display: flex;
  align-items: center;
  background-color: #f2f3f5;
  border-radius: 16px;
  padding: 2px;
  margin-top: 6px;
}

.mode-item {
  padding: 4px 14px;
  font-size: 12px;
  color: #666;
  border-radius: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 2px;
}

.mode-item.active {
  background-color: #fff;
  color: #1989fa;
  font-weight: 600;
}

.mode-item.disabled {
  opacity: 0.5;
}

.mode-check {
  font-size: 12px;
}
</style>
