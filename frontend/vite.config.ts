import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 开发模式下将 /api 代理到本地 FastAPI 服务
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
