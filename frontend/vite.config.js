import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  server: { proxy: { '/api': 'http://backend:8000', '/ws': { target: 'ws://backend:8000', ws: true } } },
  test: { environment: 'jsdom', globals: true, setupFiles: [], include: ['src/**/*.{test,spec}.{js,ts}'] }
})
