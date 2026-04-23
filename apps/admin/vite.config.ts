import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

function manualChunks(id: string) {
  if (!id.includes('/node_modules/')) {
    return undefined;
  }

  if (id.includes('/react/') || id.includes('/react-dom/') || id.includes('/scheduler/')) {
    return 'react-vendor';
  }

  if (id.includes('/react-router') || id.includes('/@remix-run/')) {
    return 'router-vendor';
  }

  if (id.includes('/@tanstack/')) {
    return 'query-vendor';
  }

  if (id.includes('/axios/') || id.includes('/zustand/') || id.includes('/jwt-decode/')) {
    return 'data-vendor';
  }

  return undefined;
}

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
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/admin/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: ['.sealosbja.site', '.xinanpcb.com'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
});
