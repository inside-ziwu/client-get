import type { Config } from 'tailwindcss';
import tailwindcssAnimate from 'tailwindcss-animate';

const sharedPreset = {
  darkMode: ['class'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        ui: {
          primary: 'var(--ui-primary)',
          'primary-active': 'var(--ui-primary-active)',
          'primary-disabled': 'var(--ui-primary-disabled)',
          'on-primary': 'var(--ui-on-primary)',
          canvas: 'var(--ui-canvas)',
          foreground: 'var(--ui-foreground)',
          body: 'var(--ui-body)',
          'muted-foreground': 'var(--ui-muted-foreground)',
          'surface-soft': 'var(--ui-surface-soft)',
          'surface-card': 'var(--ui-surface-card)',
          border: 'var(--ui-border)',
          'border-soft': 'var(--ui-border-soft)',
          'success-surface': 'var(--ui-success-surface)',
          'success-foreground': 'var(--ui-success-foreground)',
          'warning-surface': 'var(--ui-warning-surface)',
          'warning-foreground': 'var(--ui-warning-foreground)',
          'info-surface': 'var(--ui-info-surface)',
          'info-foreground': 'var(--ui-info-foreground)',
          'danger-surface': 'var(--ui-danger-surface)',
          'danger-foreground': 'var(--ui-danger-foreground)',
          overlay: 'var(--ui-overlay)',
        },
      },
      fontFamily: {
        ui: ['ui-sans-serif', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      fontSize: {
        'ui-page-title': ['20px', { fontWeight: '600', lineHeight: '1.4' }],
        'ui-section-title': ['16px', { fontWeight: '600', lineHeight: '1.4' }],
        'ui-body': ['14px', { fontWeight: '400', lineHeight: '1.5' }],
        'ui-body-strong': ['14px', { fontWeight: '500', lineHeight: '1.5' }],
        'ui-caption': ['12px', { fontWeight: '500', lineHeight: '1.4' }],
        'ui-numeric': ['14px', { fontWeight: '400', lineHeight: '1.5' }],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        'ui-xs': 'var(--ui-radius-xs)',
        'ui-sm': 'var(--ui-radius-sm)',
        'ui-md': 'var(--ui-radius-md)',
        'ui-lg': 'var(--ui-radius-lg)',
        'ui-xl': 'var(--ui-radius-xl)',
        'ui-pill': 'var(--ui-radius-pill)',
      },
      spacing: {
        'ui-xxs': 'var(--ui-spacing-xxs)',
        'ui-xs': 'var(--ui-spacing-xs)',
        'ui-sm': 'var(--ui-spacing-sm)',
        'ui-md': 'var(--ui-spacing-md)',
        'ui-lg': 'var(--ui-spacing-lg)',
        'ui-xl': 'var(--ui-spacing-xl)',
        'ui-xxl': 'var(--ui-spacing-xxl)',
      },
      width: {
        'ui-table-sm': 'var(--ui-table-column-sm)',
        'ui-table-md': 'var(--ui-table-column-md)',
        'ui-table-lg': 'var(--ui-table-column-lg)',
        'ui-table-xl': 'var(--ui-table-column-xl)',
      },
      minWidth: {
        'ui-table-sm': 'var(--ui-table-column-sm)',
        'ui-table-md': 'var(--ui-table-column-md)',
        'ui-table-lg': 'var(--ui-table-column-lg)',
        'ui-table-xl': 'var(--ui-table-column-xl)',
      },
      maxWidth: {
        'ui-table-sm': 'var(--ui-table-column-sm)',
        'ui-table-md': 'var(--ui-table-column-md)',
        'ui-table-lg': 'var(--ui-table-column-lg)',
        'ui-table-xl': 'var(--ui-table-column-xl)',
      },
    },
  },
  plugins: [tailwindcssAnimate],
} satisfies Partial<Config>;

export default sharedPreset;
