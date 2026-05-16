import type { NextConfig } from 'next';
import { PHASE_DEVELOPMENT_SERVER } from 'next/constants';
import path from 'node:path';

export default function nextConfig(phase: string): NextConfig {
  const tenantApiRewriteTarget =
    process.env.TENANT_API_REWRITE_TARGET ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

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
          source: '/t/:path*',
          destination: `${tenantApiRewriteTarget}/t/:path*`,
        },
      ];
    },
  };
}
