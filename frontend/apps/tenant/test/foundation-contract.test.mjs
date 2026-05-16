import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const read = (file) => readFileSync(path.join(root, file), 'utf8');
const exists = (file) => existsSync(path.join(root, file));

const checks = [
  ['package.json exists', () => exists('package.json')],
  ['uses Next.js', () => read('package.json').includes('"next"')],
  ['uses App Router app directory', () => exists('src/app/layout.tsx')],
  ['has providers', () => exists('src/providers.tsx')],
  ['has tenant API client', () => exists('src/lib/api.ts')],
  ['configures standalone output', () => read('next.config.ts').includes("output: 'standalone'")],
  ['configures /t rewrites', () => read('next.config.ts').includes("source: '/t/:path*'")],
  ['transpiles shared packages', () => read('next.config.ts').includes("'@shared/ui'")],
  ['uses shared Tailwind preset', () => read('tailwind.config.ts').includes('shared-ui/src/theme/tailwind-preset')],
  ['scans shared-ui content', () => read('tailwind.config.ts').includes('../../packages/shared-ui/src')],
  ['imports shared UI globals', () => read('src/app/globals.css').includes('shared-ui/src/theme/globals.css')],
  ['has login page', () => exists('src/app/login/page.tsx')],
  ['has dashboard page', () => exists('src/app/(dashboard)/page.tsx')],
  ['has health route', () => exists('src/app/api/healthz/route.ts')],
  ['has TypeScript shared aliases', () => read('tsconfig.json').includes('"@shared/ui"')],
];

for (const [name, check] of checks) {
  assert.equal(check(), true, name);
}

console.log(`foundation contract passed: ${checks.length} checks`);
