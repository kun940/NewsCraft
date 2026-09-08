<template>
  <div class="app">
    <router-view v-slot="{ Component }">
      <keep-alive :include="keepAliveNames">
        <component :is="Component" />
      </keep-alive>
    </router-view>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import router from './router'

// 需要缓存的组件名 = 路由 meta.keepAlive=true 的路由 name（与各 SFC 组件名一致）。
// keep-alive 必须常驻包裹 router-view，才能让缓存跨路由存活；
// 若用 v-if 卸载 keep-alive，进入详情页时缓存随之销毁，
// 返回列表页会重新挂载并丢失 tab / 滚动位置（表现为"返回总是回到头条"）。
const keepAliveNames = computed(() =>
  router
    .getRoutes()
    .filter((r) => r.meta.keepAlive)
    .map((r) => r.name)
)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 16px;
  background-color: #f7f8fa;
  color: #333;
  height: 100%;
  width: 100%;
}

.app {
  max-width: 750px;
  margin: 0 auto;
  height: 100%;
}

/* 移动端适配 */
@media screen and (max-width: 750px) {
  html {
    font-size: calc(100vw / 750 * 16);
  }
}
</style>
