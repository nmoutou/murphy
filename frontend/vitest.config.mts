import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

// Vitest tourne hors de Next : seul l'alias `@/*` du tsconfig est répété ici
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
