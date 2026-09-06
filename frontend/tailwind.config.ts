import type { Config } from 'tailwindcss';
import animate from 'tailwindcss-animate';

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: { center: true, padding: '1.5rem', screens: { '2xl': '1200px' } },
    extend: {
      fontFamily: {
        sans: ['"Atkinson Hyperlegible"', '"Noto Sans Bengali Variable"', 'system-ui', 'sans-serif'],
        heading: ['"Crimson Pro Variable"', '"Noto Sans Bengali Variable"', 'Georgia', 'serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
        success: { DEFAULT: 'hsl(var(--success))', foreground: 'hsl(var(--success-foreground))' },
        brand: { DEFAULT: 'hsl(var(--brand))', foreground: 'hsl(var(--brand-foreground))' },
        measure: 'hsl(var(--measure))',
        ai: { DEFAULT: 'hsl(var(--ai-surface))', border: 'hsl(var(--ai-border))', foreground: 'hsl(var(--ai-foreground))' },
        sev: {
          info: 'hsl(var(--sev-info))',
          'info-fg': 'hsl(var(--sev-info-fg))',
          low: 'hsl(var(--sev-low))',
          'low-fg': 'hsl(var(--sev-low-fg))',
          medium: 'hsl(var(--sev-medium))',
          'medium-fg': 'hsl(var(--sev-medium-fg))',
          high: 'hsl(var(--sev-high))',
          'high-fg': 'hsl(var(--sev-high-fg))',
        },
      },
      borderRadius: { lg: 'var(--radius-lg)', md: 'var(--radius)', sm: 'var(--radius-sm)' },
      transitionDuration: { DEFAULT: 'var(--dur)', fast: 'var(--dur-fast)' },
      fontSize: {
        xs: ['0.8125rem', { lineHeight: '1.25rem' }],
        sm: ['0.9375rem', { lineHeight: '1.375rem' }],
        base: ['1rem', { lineHeight: '1.6rem' }],
      },
    },
  },
  plugins: [animate],
} satisfies Config;
