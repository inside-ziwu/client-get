import { resolve } from 'node:path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@shared/types': resolve(__dirname, '../../packages/shared-types/src'),
      '@shared/api': resolve(__dirname, '../../packages/shared-api/src'),
      '@shared/hooks': resolve(__dirname, '../../packages/shared-hooks/src'),
      '@shared/ui': resolve(__dirname, '../../packages/shared-ui/src'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./test/setup.ts'],
    include: ['test/**/*.test.{ts,tsx}'],
    passWithNoTests: true,
  },
});
