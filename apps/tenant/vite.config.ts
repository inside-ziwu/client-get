import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@shared/types': path.resolve(__dirname, '../../packages/shared-types/src'),
      '@shared/api': path.resolve(__dirname, '../../packages/shared-api/src'),
      '@shared/hooks': path.resolve(__dirname, '../../packages/shared-hooks/src'),
      '@shared/ui': path.resolve(__dirname, '../../packages/shared-ui/src'),
    },
  },
  server: {
    port: 3001,
    proxy: {
      '/t/': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
