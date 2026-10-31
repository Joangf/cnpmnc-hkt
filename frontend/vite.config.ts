import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// `npm run dev` proxies to the dev-exposed backend / mock-payment ports (docker-compose.override.yml).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/mock-payment': {
        target: 'http://localhost:8200',
        rewrite: (path) => path.replace(/^\/mock-payment/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
