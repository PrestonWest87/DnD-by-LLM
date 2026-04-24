import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['all', 'dnd.weasts.net'],
    proxy: {
      '/api': {
        target: 'http://dragonforge-api-1:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    allowedHosts: ['all'],
  }
})