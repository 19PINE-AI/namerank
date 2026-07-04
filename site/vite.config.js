import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the built site works at any mount path (e.g. /research/namerank/)
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 900,
  },
})
