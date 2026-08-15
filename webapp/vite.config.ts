import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    port: 5173,
    // Telefondan sinash uchun tarmoqqa ochiq
    host: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
