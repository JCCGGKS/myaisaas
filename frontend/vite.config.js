import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  // 从 .env 读取（Vite 不会把 .env 注入 process.env，必须用 loadEnv）
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BACKEND_URL || 'http://localhost:8000'
  return {
    plugins: [vue()],
    server: {
      host: true,
      port: 5173,
      proxy: {
        // 开发时将 /api 代理到后端 FastAPI 服务
        '/api': {
          target: backendUrl,
          changeOrigin: true
        }
      }
    }
  }
})
