import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

// Tests run on Vite, outside Next: only the `@/*` alias of tsconfig is repeated here
export default defineConfig({
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['src/__tests__/setup.ts'],
  },
});
