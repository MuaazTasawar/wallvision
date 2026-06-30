import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        app: {
          bg:        'var(--bg)',
          surface:   'var(--surface)',
          card:      'var(--card)',
          border:    'var(--border)',
          text:      'var(--text)',
          'text-dim':'var(--text-dim)',
          accent:    'var(--accent)',
          'accent-text': 'var(--accent-text)',
          good:      'var(--good)',
          warn:      'var(--warn)',
          bad:       'var(--bad)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
        pill: '999px',
      },
    },
  },
  plugins: [],
}

export default config