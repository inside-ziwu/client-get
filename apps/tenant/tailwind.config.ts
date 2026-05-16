import type { Config } from 'tailwindcss';
import sharedPreset from '../../packages/shared-ui/src/theme/tailwind-preset';

const config: Config = {
  presets: [sharedPreset],
  content: ['./src/**/*.{ts,tsx}', '../../packages/shared-ui/src/**/*.{ts,tsx}'],
};

export default config;
