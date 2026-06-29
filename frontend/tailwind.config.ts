import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        radar: {
          bg:         '#080c10',
          surface:    '#0d1117',
          panel:      '#0f1923',
          border:     '#1a2332',
          orange:     '#f97316',
          'orange-dim': '#7c3a12',
          green:      '#00ff88',
          'green-dim': '#004d29',
          cyan:       '#06b6d4',
          red:        '#ef4444',
          muted:      '#4a5568',
          text:       '#e2e8f0',
          'text-dim': '#718096',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}

export default config