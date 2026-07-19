import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    // Honor an assigned dev port (e.g. from the Claude Code preview harness).
    port: process.env.PORT ? Number(process.env.PORT) : undefined,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
