import type { NextConfig } from 'next';
import { PHASE_DEVELOPMENT_SERVER } from 'next/constants';
import path from 'node:path';

export default function nextConfig(phase: string): NextConfig {
  return {
    output: 'standalone',
    outputFileTracingRoot: path.join(__dirname, '../..'),
    transpilePackages: ['@shared/api', '@shared/types', '@shared/hooks', '@shared/ui'],
    async rewrites() {
      if (phase !== PHASE_DEVELOPMENT_SERVER) {
        return [];
      }

      return [
        {
          source: '/admin/api/:path*',
          destination: 'http://localhost:8000/admin/api/:path*',
        },
      ];
    },
  };
}
