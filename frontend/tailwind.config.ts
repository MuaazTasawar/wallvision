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
        scope: {
          bg:          '#0a0e0a',
          surface:     '#0e130c',
          panel:       '#141a12',
          'panel-2':   '#182015',
          border:      '#2a3326',
          'border-lit':'#3d4a35',
          phosphor:    '#8fd13f',
          'phosphor-dim': '#3d4d2a',
          'phosphor-glow': 'rgba(143, 209, 63, 0.18)',
          amber:       '#e8973a',
          'amber-dim': '#5c3d18',
          'amber-glow':'rgba(232, 151, 58, 0.18)',
          steel:       '#6b8a9e',
          'steel-dim': '#2e3d44',
          danger:      '#c5524a',
          text:        '#d8ddd0',
          'text-dim':  '#6f7a64',
          'text-faint':'#4a5440',
        },
      },
      fontFamily: {
        mono: ['IBM Plex Mono', 'monospace'],
        display: ['Space Grotesk', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config