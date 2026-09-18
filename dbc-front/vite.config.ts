import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 8005,
    strictPort: true,
    proxy: {
      '/dbc-usercenter': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
      },
      '/dbc-manage': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
      },
      '/dbc-sqlwork': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
      },
      '/dbc-audit': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
      },
    },
  },
})
