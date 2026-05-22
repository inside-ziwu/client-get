import { resolve } from 'node:path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: {
      '@shared/types': resolve(__dirname, '../shared-types/src'),
      '@shared/hooks': resolve(__dirname, '../shared-hooks/src'),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['test/**/*.test.{ts,tsx}'],
    passWithNoTests: true,
  },
});
