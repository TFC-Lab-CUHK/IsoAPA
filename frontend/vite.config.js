import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: true })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  test: {
    environment: 'node',
    include: ['src/**/__tests__/**/*.spec.js']
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: [
      '.ngrok-free.app',
      '.ngrok-free.dev',
    ],
    proxy: {
      '/api/': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/releases': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
