import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
server: {
    // 关键配置：允许这个外部域名访问
    allowedHosts: [
      'consistently-investing-generates-ver.trycloudflare.com',
      // 也可以直接写 true，允许所有主机（临时演示用没问题）
      // allowedHosts: true
    ]
  }
})
