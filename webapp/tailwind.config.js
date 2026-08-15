import animate from 'tailwindcss-animate'

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      // shadcn/ui odatda hsl(var(--token)) ishlatadi. Bu yerda tokenlar
      // to'g'ridan-to'g'ri rang qiymatlari — chunki ular Telegram bergan
      // --tg-theme-* o'zgaruvchilaridan keladi va ular HEX ko'rinishida.
      colors: {
        background: 'var(--app-bg)',
        foreground: 'var(--app-fg)',
        muted: {
          DEFAULT: 'var(--app-muted)',
          foreground: 'var(--app-muted-fg)',
        },
        card: {
          DEFAULT: 'var(--app-card)',
          foreground: 'var(--app-fg)',
        },
        primary: {
          DEFAULT: 'var(--app-primary)',
          foreground: 'var(--app-primary-fg)',
        },
        secondary: {
          DEFAULT: 'var(--app-muted)',
          foreground: 'var(--app-fg)',
        },
        accent: {
          DEFAULT: 'var(--app-muted)',
          foreground: 'var(--app-fg)',
        },
        destructive: {
          DEFAULT: 'var(--app-destructive)',
          foreground: 'var(--app-primary-fg)',
        },
        success: {
          DEFAULT: 'var(--app-success)',
          foreground: 'var(--app-primary-fg)',
        },
        border: 'var(--app-border)',
        input: 'var(--app-border)',
        ring: 'var(--app-primary)',
      },
      borderRadius: {
        lg: '12px',
        md: '10px',
        sm: '8px',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'none' },
        },
      },
      animation: {
        'fade-in': 'fade-in 150ms ease-out',
      },
    },
  },
  plugins: [animate],
}
